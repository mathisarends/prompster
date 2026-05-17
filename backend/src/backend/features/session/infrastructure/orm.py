from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import JSON, Column, DateTime
from sqlmodel import Field, Relationship

from backend.infrastructure.database.orm import DatabaseEntity


class SessionEntity(DatabaseEntity, table=True):
    __tablename__ = "sessions"

    title: str
    owner_id: UUID = Field(index=True)
    last_activity_at: datetime = Field(sa_type=DateTime(timezone=True))

    messages: list["SessionMessageEntity"] = Relationship(
        back_populates="session",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "order_by": "SessionMessageEntity.position",
        },
    )
    playlist: Optional["SessionPlaylistEntity"] = Relationship(
        back_populates="session",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "uselist": False,
        },
    )


class SessionMessageEntity(DatabaseEntity, table=True):
    __tablename__ = "session_messages"

    session_id: UUID = Field(foreign_key="sessions.id")
    position: int
    role: str
    content: str
    tool_call_group: dict[str, object] | None = Field(
        default=None,
        sa_column=Column(JSON, nullable=True),
    )
    follow_up_group: dict[str, object] | None = Field(
        default=None,
        sa_column=Column(JSON, nullable=True),
    )

    session: SessionEntity = Relationship(back_populates="messages")


class SessionPlaylistEntity(DatabaseEntity, table=True):
    __tablename__ = "session_playlists"

    session_id: UUID = Field(foreign_key="sessions.id", unique=True)
    name: str | None = None

    session: SessionEntity = Relationship(back_populates="playlist")
    tracks: list["PlaylistTrackEntity"] = Relationship(
        back_populates="playlist",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "order_by": "PlaylistTrackEntity.position",
        },
    )


class PlaylistTrackEntity(DatabaseEntity, table=True):
    __tablename__ = "playlist_tracks"

    playlist_id: UUID = Field(foreign_key="session_playlists.id")
    position: int
    title: str
    artist: str
    year: int | None = None
    cover_url: str | None = None

    playlist: SessionPlaylistEntity = Relationship(back_populates="tracks")
