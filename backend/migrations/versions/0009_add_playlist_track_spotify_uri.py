"""Add spotify URI to playlist tracks.

Revision ID: 0009_add_playlist_track_spotify_uri
Revises: 0008_add_tool_call_status_label
Create Date: 2026-05-22 13:30:00
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0009_add_playlist_track_spotify_uri"
down_revision: Union[str, Sequence[str], None] = "0008_add_tool_call_status_label"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "playlist_tracks",
        sa.Column("spotify_uri", sa.String(length=128), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("playlist_tracks", "spotify_uri")
