"""Add is_premium flag to oauth connections.

Revision ID: 0013_add_oauth_connection_is_premium
Revises: 0012_add_session_playlist_spotify_id
Create Date: 2026-05-23 12:00:00
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0013_add_oauth_connection_is_premium"
down_revision: Union[str, Sequence[str], None] = "0012_add_session_playlist_spotify_id"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "oauth_connections",
        sa.Column(
            "is_premium",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    op.drop_column("oauth_connections", "is_premium")
