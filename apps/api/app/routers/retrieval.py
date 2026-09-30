from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth_dependencies import Principal, get_current_principal
from app.db import get_session
from app.retrieval_service import retrieve_chunks
from app.schemas import RetrievalRequest, RetrievalResponse, RetrievalResult

router = APIRouter(prefix="/retrieval", tags=["retrieval"])


@router.post("/search", response_model=RetrievalResponse)
async def search_knowledge(
    payload: RetrievalRequest,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> RetrievalResponse:
    try:
        chunks = await retrieve_chunks(
            session=session,
            organization_id=principal.organization_id,
            query=payload.query,
            top_k=payload.top_k,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="embedding provider is unavailable",
        ) from exc

    return RetrievalResponse(
        query=payload.query,
        results=[
            RetrievalResult(
                document_id=chunk.document_id,
                chunk_id=chunk.chunk_id,
                filename=chunk.filename,
                content=chunk.content,
                score=chunk.score,
                metadata=chunk.metadata,
            )
            for chunk in chunks
        ],
    )
