"""Rename workspace events to user curation events and add history index.

Revision ID: 0021_rename_workspace_events_to_user_curation_events
Revises: 0020_add_workspace_event_track_cover_url
Create Date: 2026-05-26 00:00:00
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0021_rename_workspace_events_to_user_curation_events"
down_revision: Union[str, Sequence[str], None] = (
    "0020_add_workspace_event_track_cover_url"
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.rename_table("session_workspace_events", "session_user_curation_events")
    op.execute(
        "ALTER INDEX ix_session_workspace_events_session_position "
        "RENAME TO ix_session_user_curation_events_session_position"
    )
    op.execute(
        "ALTER INDEX ix_session_workspace_events_session_consumed "
        "RENAME TO ix_session_user_curation_events_session_consumed"
    )
    op.add_column(
        "session_user_curation_events",
        sa.Column("history_index", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("session_user_curation_events", "history_index")
    op.execute(
        "ALTER INDEX ix_session_user_curation_events_session_position "
        "RENAME TO ix_session_workspace_events_session_position"
    )
    op.execute(
        "ALTER INDEX ix_session_user_curation_events_session_consumed "
        "RENAME TO ix_session_workspace_events_session_consumed"
    )
    op.rename_table("session_user_curation_events", "session_workspace_events")
