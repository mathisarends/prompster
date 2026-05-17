"""Add playlist column to sessions

Revision ID: 0002_add_session_playlist
Revises: 0001_initial_schema
Create Date: 2026-05-17 00:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0002_add_session_playlist"
down_revision: Union[str, Sequence[str], None] = "0001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "sessions",
        sa.Column("playlist", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("sessions", "playlist")
