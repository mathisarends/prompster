"""Rename playlist track is_locked to is_pinned.

Revision ID: 0016_rename_playlist_track_is_locked_to_is_pinned
Revises: 0015_add_playlist_track_is_locked
Create Date: 2026-05-24 00:00:00
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0016_rename_playlist_track_is_locked_to_is_pinned"
down_revision: Union[str, Sequence[str], None] = "0015_add_playlist_track_is_locked"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(*, table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return any(col["name"] == column_name for col in inspector.get_columns(table_name))


def upgrade() -> None:
    has_is_locked = _has_column(table_name="playlist_tracks", column_name="is_locked")
    has_is_pinned = _has_column(table_name="playlist_tracks", column_name="is_pinned")

    if has_is_locked and not has_is_pinned:
        op.alter_column(
            "playlist_tracks",
            "is_locked",
            existing_type=sa.Boolean(),
            existing_nullable=False,
            existing_server_default=sa.text("false"),
            new_column_name="is_pinned",
        )
    elif not has_is_pinned:
        op.add_column(
            "playlist_tracks",
            sa.Column(
                "is_pinned",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            ),
        )

    op.execute(
        sa.text("UPDATE playlist_tracks SET is_pinned = false WHERE is_pinned IS NULL")
    )

    op.alter_column(
        "playlist_tracks",
        "is_pinned",
        existing_type=sa.Boolean(),
        nullable=False,
        server_default=sa.text("false"),
    )


def downgrade() -> None:
    has_is_pinned = _has_column(table_name="playlist_tracks", column_name="is_pinned")
    has_is_locked = _has_column(table_name="playlist_tracks", column_name="is_locked")

    if has_is_pinned and not has_is_locked:
        op.alter_column(
            "playlist_tracks",
            "is_pinned",
            existing_type=sa.Boolean(),
            existing_nullable=False,
            existing_server_default=sa.text("false"),
            new_column_name="is_locked",
        )
    elif not has_is_locked:
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
