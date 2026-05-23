"""Add spotify playlist id to session playlists.

Revision ID: 0012_add_session_playlist_spotify_id
Revises: 0011_add_users_profile_image_url
Create Date: 2026-05-23 11:00:00
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0012_add_session_playlist_spotify_id"
down_revision: Union[str, Sequence[str], None] = "0011_add_users_profile_image_url"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "session_playlists",
        sa.Column("spotify_playlist_id", sa.String(length=64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("session_playlists", "spotify_playlist_id")
