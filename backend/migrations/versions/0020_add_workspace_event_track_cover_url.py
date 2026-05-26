"""Add track_cover_url to session workspace events.

Revision ID: 0020_add_workspace_event_track_cover_url
Revises: 0019_add_tool_call_action_type
Create Date: 2026-05-26 00:00:00
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0020_add_workspace_event_track_cover_url"
down_revision: Union[str, Sequence[str], None] = "0019_add_tool_call_action_type"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "session_workspace_events",
        sa.Column("track_cover_url", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("session_workspace_events", "track_cover_url")
