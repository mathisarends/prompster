"""Add is_locked flag to playlist tracks.

Revision ID: 0015_add_playlist_track_is_locked
Revises: 0014_repair_oauth_connection_is_premium_column
Create Date: 2026-05-24 00:00:00
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0015_add_playlist_track_is_locked"
down_revision: Union[str, Sequence[str], None] = (
    "0014_repair_oauth_connection_is_premium_column"
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(*, table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return any(col["name"] == column_name for col in inspector.get_columns(table_name))


def upgrade() -> None:
    if not _has_column(table_name="playlist_tracks", column_name="is_locked"):
        op.add_column(
            "playlist_tracks",
            sa.Column(
                "is_locked",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            ),
        )

    op.execute(
        sa.text("UPDATE playlist_tracks SET is_locked = false WHERE is_locked IS NULL")
    )

    op.alter_column(
        "playlist_tracks",
        "is_locked",
        existing_type=sa.Boolean(),
        nullable=False,
        server_default=sa.text("false"),
    )


def downgrade() -> None:
    if _has_column(table_name="playlist_tracks", column_name="is_locked"):
        op.drop_column("playlist_tracks", "is_locked")
