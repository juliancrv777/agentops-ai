"""add document ingestion metadata and vector index

Revision ID: 20260930_0003
Revises: 20260930_0002
Create Date: 2026-09-30
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260930_0003"
down_revision: Union[str, Sequence[str], None] = "20260930_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column("mime_type", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "documents",
        sa.Column("size_bytes", sa.BigInteger(), nullable=True),
    )
    op.add_column(
        "documents",
        sa.Column("content_sha256", sa.String(length=64), nullable=True),
    )
    op.create_unique_constraint(
        "uq_documents_org_sha256",
        "documents",
        ["organization_id", "content_sha256"],
    )
    op.create_unique_constraint(
        "uq_document_chunk_index",
        "document_chunks",
        ["document_id", "chunk_index"],
    )
    op.execute(
        "CREATE INDEX ix_document_chunks_embedding_hnsw "
        "ON document_chunks USING hnsw (embedding vector_cosine_ops) "
        "WHERE embedding IS NOT NULL"
    )


def downgrade() -> None:
    op.drop_index(
        "ix_document_chunks_embedding_hnsw",
        table_name="document_chunks",
    )
    op.drop_constraint(
        "uq_document_chunk_index",
        "document_chunks",
        type_="unique",
    )
    op.drop_constraint(
        "uq_documents_org_sha256",
        "documents",
        type_="unique",
    )
    op.drop_column("documents", "content_sha256")
    op.drop_column("documents", "size_bytes")
    op.drop_column("documents", "mime_type")
