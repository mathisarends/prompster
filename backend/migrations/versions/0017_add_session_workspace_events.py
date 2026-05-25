"""Add session workspace events table.

Revision ID: 0017_add_session_workspace_events
Revises: 0016_rename_playlist_track_is_locked_to_is_pinned
Create Date: 2026-05-25 00:00:00
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0017_add_session_workspace_events"
down_revision: Union[str, Sequence[str], None] = (
    "0016_rename_playlist_track_is_locked_to_is_pinned"
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "session_workspace_events",
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
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("track_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("track_title", sa.Text(), nullable=False),
        sa.Column("track_artist", sa.Text(), nullable=False),
        sa.Column("track_spotify_uri", sa.String(length=128), nullable=True),
        sa.Column(
            "consumed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_session_workspace_events_session_position",
        "session_workspace_events",
        ["session_id", "position"],
        unique=False,
    )
    op.create_index(
        "ix_session_workspace_events_session_consumed",
        "session_workspace_events",
        ["session_id", "consumed"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_session_workspace_events_session_consumed",
        table_name="session_workspace_events",
    )
    op.drop_index(
        "ix_session_workspace_events_session_position",
        table_name="session_workspace_events",
    )
    op.drop_table("session_workspace_events")
