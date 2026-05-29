"""Add session playlist and artist references.

Revision ID: 0024_add_session_references
Revises: 0023_add_user_message_quotas
Create Date: 2026-05-29 00:00:00
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0024_add_session_references"
down_revision: Union[str, Sequence[str], None] = "0023_add_user_message_quotas"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "session_playlist_references",
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
        sa.Column("spotify_playlist_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("owner", sa.String(), nullable=True),
        sa.Column("cover_url", sa.String(), nullable=True),
        sa.Column("total_tracks", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "session_id",
            "spotify_playlist_id",
            name="uq_session_playlist_references_session_spotify_playlist",
        ),
    )
    op.create_index(
        "ix_session_playlist_references_session_position",
        "session_playlist_references",
        ["session_id", "position"],
        unique=False,
    )

    op.create_table(
        "session_artist_references",
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
        sa.Column("spotify_artist_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("image_url", sa.String(), nullable=True),
        sa.Column(
            "genres",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("followers", sa.Integer(), nullable=True),
        sa.Column("popularity", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "session_id",
            "spotify_artist_id",
            name="uq_session_artist_references_session_spotify_artist",
        ),
    )
    op.create_index(
        "ix_session_artist_references_session_position",
        "session_artist_references",
        ["session_id", "position"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_session_artist_references_session_position",
        table_name="session_artist_references",
    )
    op.drop_table("session_artist_references")
    op.drop_index(
        "ix_session_playlist_references_session_position",
        table_name="session_playlist_references",
    )
    op.drop_table("session_playlist_references")
