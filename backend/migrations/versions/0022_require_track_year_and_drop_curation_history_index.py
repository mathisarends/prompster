"""Require track year and replace curation history index with track year.

Revision ID: 0022_require_track_year_and_drop_curation_history_index
Revises: 0021_rename_workspace_events_to_user_curation_events
Create Date: 2026-05-26 00:00:00
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0022_require_track_year_and_drop_curation_history_index"
down_revision: Union[str, Sequence[str], None] = (
    "0021_rename_workspace_events_to_user_curation_events"
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(*, table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return any(col["name"] == column_name for col in inspector.get_columns(table_name))


def upgrade() -> None:
    has_track_year = _has_column(
        table_name="session_user_curation_events", column_name="track_year"
    )
    if not has_track_year:
        op.add_column(
            "session_user_curation_events",
            sa.Column("track_year", sa.Integer(), nullable=True),
        )

    if _has_column(table_name="playlist_tracks", column_name="year"):
        op.execute(
            sa.text(
                """
                UPDATE session_user_curation_events AS event
                SET track_year = track.year
                FROM playlist_tracks AS track
                WHERE event.track_year IS NULL
                  AND event.track_id = track.id
                  AND track.year IS NOT NULL
                """
            )
        )

        op.execute(sa.text("DELETE FROM playlist_tracks WHERE year IS NULL"))

        op.alter_column(
            "playlist_tracks",
            "year",
            existing_type=sa.Integer(),
            nullable=False,
        )

    if _has_column(
        table_name="session_user_curation_events", column_name="history_index"
    ):
        op.drop_column("session_user_curation_events", "history_index")


def downgrade() -> None:
    if _has_column(table_name="playlist_tracks", column_name="year"):
        op.alter_column(
            "playlist_tracks",
            "year",
            existing_type=sa.Integer(),
            nullable=True,
        )

    if not _has_column(
        table_name="session_user_curation_events", column_name="history_index"
    ):
        op.add_column(
            "session_user_curation_events",
            sa.Column("history_index", sa.Integer(), nullable=True),
        )

    if _has_column(table_name="session_user_curation_events", column_name="track_year"):
        op.drop_column("session_user_curation_events", "track_year")
