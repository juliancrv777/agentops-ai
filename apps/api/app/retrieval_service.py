from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.embeddings import get_embedding_provider
from app.models import Document, DocumentChunk


@dataclass(frozen=True)
class RetrievedChunk:
    document_id: UUID
    chunk_id: UUID
    filename: str
    content: str
    score: float
    metadata: dict


async def retrieve_chunks(
    *,
    session: AsyncSession,
    organization_id: UUID,
    query: str,
    top_k: int,
) -> list[RetrievedChunk]:
    provider = get_embedding_provider()
    vectors = await provider.embed_documents([query])
    query_embedding = vectors[0]

    distance = DocumentChunk.embedding.cosine_distance(query_embedding).label(
        "distance"
    )

    statement = (
        select(DocumentChunk, Document.filename, distance)
        .join(Document, Document.id == DocumentChunk.document_id)
        .where(
            DocumentChunk.organization_id == organization_id,
            DocumentChunk.embedding.is_not(None),
            Document.status == "ready",
        )
        .order_by(distance)
        .limit(top_k)
    )

    rows = (await session.execute(statement)).all()
    results: list[RetrievedChunk] = []

    for chunk, filename, raw_distance in rows:
        similarity = 1.0 - float(raw_distance)
        similarity = max(-1.0, min(1.0, similarity))

        results.append(
            RetrievedChunk(
                document_id=chunk.document_id,
                chunk_id=chunk.id,
                filename=filename,
                content=chunk.content,
                score=round(similarity, 6),
                metadata=chunk.chunk_metadata,
            )
        )

    return results
