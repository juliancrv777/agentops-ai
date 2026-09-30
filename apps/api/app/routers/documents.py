import hashlib
from pathlib import Path

from anyio import to_thread
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth_dependencies import Principal, get_current_principal
from app.config import get_settings
from app.db import get_session
from app.embeddings import get_embedding_provider
from app.models import Document, DocumentChunk
from app.schemas import DocumentResponse
from app.storage import save_upload
from app.text_processing import SUPPORTED_EXTENSIONS, chunk_segments, extract_segments

router = APIRouter(prefix="/documents", tags=["documents"])
settings = get_settings()


def _document_response(document: Document) -> DocumentResponse:
    return DocumentResponse(
        id=document.id,
        filename=document.filename,
        mime_type=document.mime_type,
        size_bytes=document.size_bytes,
        status=document.status,
        created_at=document.created_at,
    )


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> DocumentResponse:
    filename = Path(file.filename or "document").name
    suffix = Path(filename).suffix.lower()

    if suffix not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="supported document types are .txt, .md, and .pdf",
        )

    content = await file.read(settings.max_upload_bytes + 1)
    if not content:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="document is empty",
        )
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="document exceeds upload size limit",
        )

    content_sha256 = hashlib.sha256(content).hexdigest()

    duplicate = await session.scalar(
        select(Document).where(
            Document.organization_id == principal.organization_id,
            Document.content_sha256 == content_sha256,
        )
    )
    if duplicate is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="this document content already exists in the organization",
        )

    document = Document(
        organization_id=principal.organization_id,
        filename=filename,
        mime_type=file.content_type,
        size_bytes=len(content),
        content_sha256=content_sha256,
        status="processing",
    )
    session.add(document)

    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="this document content already exists in the organization",
        ) from None

    await session.refresh(document)

    try:
        object_key = await save_upload(
            principal.organization_id,
            document.id,
            filename,
            content,
        )

        segments = await to_thread.run_sync(extract_segments, filename, content)
        chunks = await to_thread.run_sync(chunk_segments, segments)

        if not chunks:
            raise ValueError("no extractable text found")

        provider = get_embedding_provider()
        embeddings = await provider.embed_documents(
            [chunk.content for chunk in chunks]
        )

        if len(embeddings) != len(chunks):
            raise RuntimeError("embedding provider returned an unexpected result count")

        for index, (chunk, embedding) in enumerate(zip(chunks, embeddings, strict=True)):
            session.add(
                DocumentChunk(
                    organization_id=principal.organization_id,
                    document_id=document.id,
                    chunk_index=index,
                    content=chunk.content,
                    chunk_metadata={
                        **chunk.metadata,
                        "source": filename,
                        "embedding_provider": provider.name,
                        "embedding_model": provider.model,
                    },
                    embedding=embedding,
                )
            )

        document.object_key = object_key
        document.status = "ready"
        await session.commit()
        await session.refresh(document)
        return _document_response(document)

    except Exception as exc:
        await session.rollback()
        failed_document = await session.get(Document, document.id)
        if failed_document is not None:
            failed_document.status = "failed"
            await session.commit()

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="document processing failed",
        ) from exc


@router.get("", response_model=list[DocumentResponse])
async def list_documents(
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> list[DocumentResponse]:
    documents = (
        await session.scalars(
            select(Document)
            .where(Document.organization_id == principal.organization_id)
            .order_by(Document.created_at.desc())
        )
    ).all()

    return [_document_response(document) for document in documents]
