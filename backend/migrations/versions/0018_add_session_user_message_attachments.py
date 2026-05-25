"""Add user message attachment references.

Revision ID: 0018_add_session_user_message_attachments
Revises: 0017_add_session_workspace_events
Create Date: 2026-05-25 00:30:00
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0018_add_session_user_message_attachments"
down_revision: Union[str, Sequence[str], None] = "0017_add_session_workspace_events"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "session_user_message_attachments",
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
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=64), nullable=False),
        sa.Column("external_id", sa.String(length=128), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("subtitle", sa.Text(), nullable=True),
        sa.Column("image_url", sa.Text(), nullable=True),
        sa.Column("spotify_id", sa.String(length=128), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_session_user_message_attachments_message_position",
        "session_user_message_attachments",
        ["user_message_id", "position"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_session_user_message_attachments_message_position",
        table_name="session_user_message_attachments",
    )
    op.drop_table("session_user_message_attachments")
