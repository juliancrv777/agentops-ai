from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth_dependencies import Principal, get_current_principal
from app.db import get_session
from app.embeddings import get_embedding_provider
from app.models import Document, DocumentChunk
from app.schemas import RetrievalRequest, RetrievalResponse, RetrievalResult

router = APIRouter(prefix="/retrieval", tags=["retrieval"])


@router.post("/search", response_model=RetrievalResponse)
async def search_knowledge(
    payload: RetrievalRequest,
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> RetrievalResponse:
    try:
        provider = get_embedding_provider()
        vectors = await provider.embed_documents([payload.query])
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="embedding provider is unavailable",
        ) from exc

    query_embedding = vectors[0]
    distance = DocumentChunk.embedding.cosine_distance(query_embedding).label(
        "distance"
    )

    statement = (
        select(DocumentChunk, Document.filename, distance)
        .join(Document, Document.id == DocumentChunk.document_id)
        .where(
            DocumentChunk.organization_id == principal.organization_id,
            DocumentChunk.embedding.is_not(None),
            Document.status == "ready",
        )
        .order_by(distance)
        .limit(payload.top_k)
    )

    rows = (await session.execute(statement)).all()
    results: list[RetrievalResult] = []

    for chunk, filename, raw_distance in rows:
        similarity = 1.0 - float(raw_distance)
        similarity = max(-1.0, min(1.0, similarity))

        results.append(
            RetrievalResult(
                document_id=chunk.document_id,
                chunk_id=chunk.id,
                filename=filename,
                content=chunk.content,
                score=round(similarity, 6),
                metadata=chunk.chunk_metadata,
            )
        )

    return RetrievalResponse(query=payload.query, results=results)
