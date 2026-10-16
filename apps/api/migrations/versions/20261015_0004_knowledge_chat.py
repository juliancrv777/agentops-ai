"""Persist tenant-scoped private knowledge conversations.

Revision ID: 20261015_0004
Revises: 20260930_0003
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20261015_0004"
down_revision: Union[str, Sequence[str], None] = "20260930_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "chat_conversations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"],
                                ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"],
                                ondelete="CASCADE"),
    )
    op.create_index("ix_chat_conversations_organization_id",
                    "chat_conversations", ["organization_id"])
    op.create_index("ix_chat_conversations_user_id",
                    "chat_conversations", ["user_id"])
    op.create_index("ix_chat_conversations_owner_recent",
                    "chat_conversations", ["organization_id", "user_id", "updated_at"])

    op.create_table(
        "chat_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("citations", postgresql.JSONB(), nullable=False,
                  server_default=sa.text("'[]'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["chat_conversations.id"],
                                ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"],
                                ondelete="CASCADE"),
        sa.CheckConstraint("role IN ('user', 'assistant')",
                           name="ck_chat_message_role"),
    )
    op.create_index("ix_chat_messages_conversation_id",
                    "chat_messages", ["conversation_id"])
    op.create_index("ix_chat_messages_organization_id",
                    "chat_messages", ["organization_id"])
    op.create_index("ix_chat_messages_order",
                    "chat_messages", ["conversation_id", "created_at", "id"])


def downgrade() -> None:
    op.drop_index("ix_chat_messages_order", table_name="chat_messages")
    op.drop_index("ix_chat_messages_organization_id", table_name="chat_messages")
    op.drop_index("ix_chat_messages_conversation_id", table_name="chat_messages")
    op.drop_table("chat_messages")
    op.drop_index("ix_chat_conversations_owner_recent",
                  table_name="chat_conversations")
    op.drop_index("ix_chat_conversations_user_id",
                  table_name="chat_conversations")
    op.drop_index("ix_chat_conversations_organization_id",
                  table_name="chat_conversations")
    op.drop_table("chat_conversations")
