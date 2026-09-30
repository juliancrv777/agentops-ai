import json
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth_dependencies import Principal, get_current_principal
from app.chat_providers import get_chat_provider
from app.config import get_settings
from app.db import SessionLocal, get_session
from app.models import ChatMessage, Conversation
from app.retrieval_service import RetrievedChunk, retrieve_chunks
from app.schemas import (
    ChatMessageRequest,
    ChatMessageResponse,
    ConversationCreateRequest,
    ConversationResponse,
)

router = APIRouter(prefix="/chat", tags=["chat"])
settings = get_settings()


def _conversation_response(conversation: Conversation) -> ConversationResponse:
    return ConversationResponse(
        id=conversation.id,
        title=conversation.title,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
    )


def _citation_payload(chunk: RetrievedChunk) -> dict:
    return {
        "document_id": str(chunk.document_id),
        "chunk_id": str(chunk.chunk_id),
        "filename": chunk.filename,
        "score": chunk.score,
        "metadata": chunk.metadata,
    }


def _sse(event: str, payload: dict) -> str:
    return (
        f"event: {event}\n"
        f"data: {json.dumps(payload, separators=(',', ':'))}\n\n"
    )


async def _owned_conversation(
    *,
    session: AsyncSession,
    conversation_id: UUID,
    principal: Principal,
) -> Conversation:
    conversation = await session.scalar(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.organization_id == principal.organization_id,
            Conversation.user_id == principal.user_id,
        )
    )

    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="conversation not found",
        )

    return conversation


@router.post(
    "/conversations",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_conversation(
    payload: ConversationCreateRequest,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> ConversationResponse:
    conversation = Conversation(
        organization_id=principal.organization_id,
        user_id=principal.user_id,
        title=(payload.title or "New chat").strip(),
    )
    session.add(conversation)
    await session.commit()
    await session.refresh(conversation)

    return _conversation_response(conversation)


@router.get(
    "/conversations",
    response_model=list[ConversationResponse],
)
async def list_conversations(
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> list[ConversationResponse]:
    conversations = (
        await session.scalars(
            select(Conversation)
            .where(
                Conversation.organization_id == principal.organization_id,
                Conversation.user_id == principal.user_id,
            )
            .order_by(Conversation.updated_at.desc())
        )
    ).all()

    return [_conversation_response(conversation) for conversation in conversations]


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=list[ChatMessageResponse],
)
async def list_messages(
    conversation_id: UUID,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> list[ChatMessageResponse]:
    await _owned_conversation(
        session=session,
        conversation_id=conversation_id,
        principal=principal,
    )

    messages = (
        await session.scalars(
            select(ChatMessage)
            .where(
                ChatMessage.organization_id == principal.organization_id,
                ChatMessage.conversation_id == conversation_id,
            )
            .order_by(ChatMessage.created_at.asc(), ChatMessage.id.asc())
        )
    ).all()

    return [
        ChatMessageResponse(
            id=message.id,
            role=message.role,
            content=message.content,
            citations=message.citations,
            created_at=message.created_at,
        )
        for message in messages
    ]


@router.post("/conversations/{conversation_id}/messages/stream")
async def stream_message(
    conversation_id: UUID,
    payload: ChatMessageRequest,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> StreamingResponse:
    conversation = await _owned_conversation(
        session=session,
        conversation_id=conversation_id,
        principal=principal,
    )

    history_rows = (
        await session.scalars(
            select(ChatMessage)
            .where(
                ChatMessage.organization_id == principal.organization_id,
                ChatMessage.conversation_id == conversation_id,
            )
            .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
            .limit(settings.chat_history_messages)
        )
    ).all()

    history = [
        (message.role, message.content)
        for message in reversed(history_rows)
        if message.role in {"user", "assistant"}
    ]

    try:
        retrieved = await retrieve_chunks(
            session=session,
            organization_id=principal.organization_id,
            query=payload.content,
            top_k=settings.chat_retrieval_top_k,
        )
        provider = get_chat_provider()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="chat dependencies are unavailable",
        ) from exc

    user_message = ChatMessage(
        organization_id=principal.organization_id,
        conversation_id=conversation.id,
        role="user",
        content=payload.content,
        citations=[],
    )
    session.add(user_message)

    if conversation.title == "New chat":
        conversation.title = payload.content.strip()[:120]

    conversation.updated_at = datetime.now(timezone.utc)
    await session.commit()

    citations = [_citation_payload(chunk) for chunk in retrieved]
    organization_id = principal.organization_id
    user_id = principal.user_id

    async def event_stream() -> AsyncIterator[str]:
        del user_id
        yield _sse(
            "sources",
            {
                "citations": citations,
                "provider": provider.name,
                "model": provider.model,
            },
        )

        parts: list[str] = []

        try:
            async for token in provider.stream_answer(
                question=payload.content,
                context=retrieved,
                history=history,
            ):
                parts.append(token)
                yield _sse("token", {"text": token})
        except Exception:
            yield _sse(
                "error",
                {"message": "The model provider failed while streaming."},
            )
            return

        answer = "".join(parts).strip()
        if not answer:
            yield _sse(
                "error",
                {"message": "The model provider returned an empty response."},
            )
            return

        async with SessionLocal() as persist_session:
            persisted_conversation = await persist_session.scalar(
                select(Conversation).where(
                    Conversation.id == conversation_id,
                    Conversation.organization_id == organization_id,
                )
            )

            if persisted_conversation is None:
                yield _sse(
                    "error",
                    {"message": "Conversation is no longer available."},
                )
                return

            assistant_message = ChatMessage(
                organization_id=organization_id,
                conversation_id=conversation_id,
                role="assistant",
                content=answer,
                citations=citations,
            )
            persisted_conversation.updated_at = datetime.now(timezone.utc)
            persist_session.add(assistant_message)
            await persist_session.commit()
            await persist_session.refresh(assistant_message)

        yield _sse(
            "done",
            {
                "message_id": str(assistant_message.id),
                "citations": citations,
            },
        )

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
