"""Remove playlist track is_pinned.

Track pinning was removed from the application; the column was left behind.

Revision ID: 0041_remove_playlist_track_is_pinned
Revises: 0040_add_session_agent_checkpoints
Create Date: 2026-11-25 00:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0041_remove_playlist_track_is_pinned"
down_revision: Union[str, Sequence[str], None] = "0040_add_session_agent_checkpoints"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("playlist_tracks", "is_pinned")


def downgrade() -> None:
    op.add_column(
        "playlist_tracks",
        sa.Column(
            "is_pinned",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
