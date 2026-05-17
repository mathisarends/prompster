"""Normalize session storage into relational tables.

Revision ID: 0003_normalize_session_storage
Revises: 0002_add_session_playlist
Create Date: 2026-05-17 12:00:00
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Sequence, Union
from uuid import UUID, uuid4

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0003_normalize_session_storage"
down_revision: Union[str, Sequence[str], None] = "0002_add_session_playlist"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "session_messages",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=True,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "tool_call_group", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column(
            "follow_up_group", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_session_messages_session_id_position",
        "session_messages",
        ["session_id", "position"],
        unique=False,
    )

    op.create_table(
        "session_playlists",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=True,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id", name="uq_session_playlists_session_id"),
    )

    op.create_table(
        "playlist_tracks",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=True,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "playlist_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("session_playlists.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("artist", sa.Text(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("cover_url", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_playlist_tracks_playlist_id_position",
        "playlist_tracks",
        ["playlist_id", "position"],
        unique=False,
    )

    op.add_column(
        "sessions",
        sa.Column("last_activity_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute("UPDATE sessions SET last_activity_at = COALESCE(created_at, now())")

    _migrate_from_json_to_relational()

    op.alter_column("sessions", "last_activity_at", nullable=False)
    op.create_index(
        "ix_sessions_owner_id_last_activity_at",
        "sessions",
        ["owner_id", "last_activity_at"],
        unique=False,
    )

    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_sessions_title_trgm ON sessions USING gin (title gin_trgm_ops)"
    )

    op.drop_column("sessions", "messages")
    op.drop_column("sessions", "playlist")


def downgrade() -> None:
    op.add_column(
        "sessions",
        sa.Column(
            "messages",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'::json"),
        ),
    )
    op.add_column("sessions", sa.Column("playlist", sa.JSON(), nullable=True))

    _migrate_from_relational_to_json()

    op.alter_column("sessions", "messages", server_default=None)

    op.execute("DROP INDEX IF EXISTS ix_sessions_title_trgm")
    op.drop_index("ix_sessions_owner_id_last_activity_at", table_name="sessions")
    op.drop_column("sessions", "last_activity_at")

    op.drop_index(
        "ix_playlist_tracks_playlist_id_position",
        table_name="playlist_tracks",
    )
    op.drop_table("playlist_tracks")

    op.drop_table("session_playlists")

    op.drop_index(
        "ix_session_messages_session_id_position",
        table_name="session_messages",
    )
    op.drop_table("session_messages")


def _migrate_from_json_to_relational() -> None:
    conn = op.get_bind()

    sessions = conn.execute(
        sa.text("SELECT id, created_at, messages, playlist FROM sessions")
    ).mappings()

    insert_message = sa.text(
        """
        INSERT INTO session_messages (
            id,
            created_at,
            session_id,
            position,
            role,
            content,
            tool_call_group,
            follow_up_group
        ) VALUES (
            :id,
            :created_at,
            :session_id,
            :position,
            :role,
            :content,
            CAST(:tool_call_group AS jsonb),
            CAST(:follow_up_group AS jsonb)
        )
        """
    )
    insert_playlist = sa.text(
        """
        INSERT INTO session_playlists (
            id,
            created_at,
            session_id,
            name
        ) VALUES (
            :id,
            :created_at,
            :session_id,
            :name
        )
        """
    )
    insert_track = sa.text(
        """
        INSERT INTO playlist_tracks (
            id,
            created_at,
            playlist_id,
            position,
            title,
            artist,
            year,
            cover_url
        ) VALUES (
            :id,
            :created_at,
            :playlist_id,
            :position,
            :title,
            :artist,
            :year,
            :cover_url
        )
        """
    )
    update_last_activity = sa.text(
        "UPDATE sessions SET last_activity_at = :last_activity_at WHERE id = :session_id"
    )

    for session_row in sessions:
        session_id = session_row["id"]
        session_created_at = _as_datetime(session_row["created_at"]) or datetime.now(
            timezone.utc
        )
        last_activity_at = session_created_at

        for position, message_payload in enumerate(
            _as_dict_list(session_row["messages"])
        ):
            message_created_at = (
                _as_datetime(message_payload.get("created_at")) or session_created_at
            )
            if message_created_at > last_activity_at:
                last_activity_at = message_created_at

            role = str(message_payload.get("role", "assistant")).lower()
            if role not in {"assistant", "user"}:
                role = "assistant"

            tool_call_group = message_payload.get("tool_call_group")
            follow_up_group = message_payload.get("follow_up_group")

            conn.execute(
                insert_message,
                {
                    "id": _as_uuid(message_payload.get("id")) or uuid4(),
                    "created_at": message_created_at,
                    "session_id": session_id,
                    "position": position,
                    "role": role,
                    "content": str(message_payload.get("content", "")),
                    "tool_call_group": (
                        json.dumps(tool_call_group)
                        if isinstance(tool_call_group, dict)
                        else None
                    ),
                    "follow_up_group": (
                        json.dumps(follow_up_group)
                        if isinstance(follow_up_group, dict)
                        else None
                    ),
                },
            )

        playlist_payload = session_row["playlist"]
        if isinstance(playlist_payload, dict):
            playlist_id = _as_uuid(playlist_payload.get("id")) or uuid4()
            playlist_created_at = (
                _as_datetime(playlist_payload.get("created_at")) or session_created_at
            )
            conn.execute(
                insert_playlist,
                {
                    "id": playlist_id,
                    "created_at": playlist_created_at,
                    "session_id": session_id,
                    "name": (
                        str(playlist_payload.get("name"))
                        if isinstance(playlist_payload.get("name"), str)
                        else None
                    ),
                },
            )

            for position, track_payload in enumerate(
                _as_dict_list(playlist_payload.get("tracks"))
            ):
                conn.execute(
                    insert_track,
                    {
                        "id": _as_uuid(track_payload.get("id")) or uuid4(),
                        "created_at": (
                            _as_datetime(track_payload.get("created_at"))
                            or playlist_created_at
                        ),
                        "playlist_id": playlist_id,
                        "position": position,
                        "title": str(track_payload.get("title", "")),
                        "artist": str(track_payload.get("artist", "")),
                        "year": _as_int(track_payload.get("year")),
                        "cover_url": (
                            str(track_payload.get("cover_url"))
                            if track_payload.get("cover_url") is not None
                            else None
                        ),
                    },
                )

        conn.execute(
            update_last_activity,
            {
                "session_id": session_id,
                "last_activity_at": last_activity_at,
            },
        )


def _migrate_from_relational_to_json() -> None:
    conn = op.get_bind()

    session_ids = conn.execute(sa.text("SELECT id FROM sessions")).scalars()

    select_messages = sa.text(
        """
        SELECT id, created_at, role, content, tool_call_group, follow_up_group
        FROM session_messages
        WHERE session_id = :session_id
        ORDER BY position
        """
    )
    select_playlist = sa.text(
        """
        SELECT id, created_at, name
        FROM session_playlists
        WHERE session_id = :session_id
        """
    )
    select_tracks = sa.text(
        """
        SELECT id, created_at, title, artist, year, cover_url
        FROM playlist_tracks
        WHERE playlist_id = :playlist_id
        ORDER BY position
        """
    )
    update_with_playlist = sa.text(
        """
        UPDATE sessions
        SET messages = CAST(:messages AS json), playlist = CAST(:playlist AS json)
        WHERE id = :session_id
        """
    )
    update_without_playlist = sa.text(
        """
        UPDATE sessions
        SET messages = CAST(:messages AS json), playlist = NULL
        WHERE id = :session_id
        """
    )

    for session_id in session_ids:
        message_rows = conn.execute(
            select_messages,
            {"session_id": session_id},
        ).mappings()

        messages_payload = []
        for message in message_rows:
            payload = {
                "id": str(message["id"]),
                "created_at": _to_iso(message["created_at"]),
                "role": message["role"],
                "content": message["content"],
                "tool_call_group": message["tool_call_group"],
                "follow_up_group": message["follow_up_group"],
            }
            messages_payload.append(payload)

        playlist_row = (
            conn.execute(
                select_playlist,
                {"session_id": session_id},
            )
            .mappings()
            .first()
        )

        if playlist_row is None:
            conn.execute(
                update_without_playlist,
                {
                    "session_id": session_id,
                    "messages": json.dumps(messages_payload),
                },
            )
            continue

        track_rows = conn.execute(
            select_tracks,
            {"playlist_id": playlist_row["id"]},
        ).mappings()
        tracks_payload = [
            {
                "id": str(track["id"]),
                "created_at": _to_iso(track["created_at"]),
                "title": track["title"],
                "artist": track["artist"],
                "year": track["year"],
                "cover_url": track["cover_url"],
            }
            for track in track_rows
        ]

        playlist_payload = {
            "id": str(playlist_row["id"]),
            "created_at": _to_iso(playlist_row["created_at"]),
            "name": playlist_row["name"],
            "tracks": tracks_payload,
        }

        conn.execute(
            update_with_playlist,
            {
                "session_id": session_id,
                "messages": json.dumps(messages_payload),
                "playlist": json.dumps(playlist_payload),
            },
        )


def _as_dict_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _as_uuid(value: Any) -> UUID | None:
    if isinstance(value, UUID):
        return value
    if isinstance(value, str) and value:
        try:
            return UUID(value)
        except ValueError:
            return None
    return None


def _as_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str) and value:
        normalized = value.replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(normalized)
        except ValueError:
            return None
    return None


def _as_int(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None


def _to_iso(value: Any) -> str:
    parsed = _as_datetime(value)
    if parsed is None:
        return datetime.now(timezone.utc).isoformat()
    return parsed.isoformat()
