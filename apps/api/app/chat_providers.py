import asyncio
from collections.abc import AsyncIterator
from functools import lru_cache

from openai import AsyncOpenAI

from app.config import get_settings
from app.retrieval_service import RetrievedChunk

settings = get_settings()


class DeterministicChatProvider:
    name = "deterministic"
    model = "grounded-template-v1"

    async def stream_answer(
        self,
        *,
        question: str,
        context: list[RetrievedChunk],
        history: list[tuple[str, str]],
    ) -> AsyncIterator[str]:
        del history

        if not context:
            answer = (
                "I could not find relevant information in the organization's "
                "knowledge base for this question."
            )
        else:
            excerpts = []
            for index, chunk in enumerate(context[:3], start=1):
                cleaned = " ".join(chunk.content.split())
                excerpts.append(
                    f"Source {index} ({chunk.filename}): {cleaned[:420]}"
                )

            answer = (
                f"Question: {question}\n\n"
                "Grounded context found in the knowledge base:\n"
                + "\n".join(excerpts)
            )

        pieces = answer.split(" ")
        for index, piece in enumerate(pieces):
            await asyncio.sleep(0)
            suffix = "" if index == len(pieces) - 1 else " "
            yield piece + suffix


class OpenAIChatProvider:
    name = "openai"

    def __init__(self, *, api_key: str, model: str) -> None:
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model

    async def stream_answer(
        self,
        *,
        question: str,
        context: list[RetrievedChunk],
        history: list[tuple[str, str]],
    ) -> AsyncIterator[str]:
        context_text = "\n\n".join(
            (
                f"[Source {index}] {chunk.filename}\n"
                f"{chunk.content}"
            )
            for index, chunk in enumerate(context, start=1)
        )

        messages: list[dict[str, str]] = [
            {
                "role": "system",
                "content": (
                    "You are AgentOps AI. Answer using the supplied knowledge "
                    "context. If the context does not support a claim, say that "
                    "you do not have enough information. Do not invent sources. "
                    "The application attaches structured citations separately."
                ),
            }
        ]

        for role, content in history:
            if role in {"user", "assistant"}:
                messages.append({"role": role, "content": content})

        messages.append(
            {
                "role": "user",
                "content": (
                    f"Knowledge context:\n{context_text or '(no matching context)'}"
                    f"\n\nQuestion:\n{question}"
                ),
            }
        )

        stream = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            stream=True,
            temperature=0.2,
        )

        async for chunk in stream:
            if not chunk.choices:
                continue
            content = chunk.choices[0].delta.content
            if content:
                yield content


@lru_cache
def get_chat_provider():
    provider = settings.chat_provider.lower().strip()

    if provider == "deterministic":
        return DeterministicChatProvider()

    if provider == "openai":
        if not settings.openai_api_key or not settings.openai_chat_model:
            raise RuntimeError(
                "OPENAI_API_KEY and OPENAI_CHAT_MODEL are required "
                "when CHAT_PROVIDER=openai"
            )
        return OpenAIChatProvider(
            api_key=settings.openai_api_key,
            model=settings.openai_chat_model,
        )

    raise RuntimeError(f"unsupported chat provider: {provider}")
