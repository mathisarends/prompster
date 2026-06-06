"""Add image attachments for user messages.

Revision ID: 0032_add_session_user_message_image_attachments
Revises: 0031_add_onboarding_question_hint
Create Date: 2026-06-06

"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0032_add_session_user_message_image_attachments"
down_revision: str | Sequence[str] | None = "0031_add_onboarding_question_hint"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "session_user_message_image_attachments",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=True,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "user_message_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("session_user_messages.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("storage_key", sa.Text(), nullable=False),
        sa.Column("content_type", sa.String(length=128), nullable=False),
        sa.Column("file_name", sa.Text(), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_session_user_message_image_attachments_user_message_id",
        "session_user_message_image_attachments",
        ["user_message_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_session_user_message_image_attachments_user_message_id",
        table_name="session_user_message_image_attachments",
    )
    op.drop_table("session_user_message_image_attachments")
