from datetime import datetime
from uuid import UUID

from sqlalchemy import JSON, Column, DateTime, Index
from sqlmodel import Field, Relationship, SQLModel, text


class DatabaseEntity(SQLModel):
    id: UUID | None = Field(
        default=None,
        primary_key=True,
        sa_column_kwargs={"server_default": text("gen_random_uuid()")},
    )
    created_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),
        sa_column_kwargs={"server_default": text("now()")},
    )


class UserModel(DatabaseEntity, table=True):
    __tablename__ = "users"

    name: str
    email: str = Field(index=True, unique=True)
    google_subject: str = Field(index=True, unique=True)


class SessionModel(DatabaseEntity, table=True):
    __tablename__ = "sessions"
    __table_args__ = (
        Index("ix_sessions_owner_activity", "owner_id", "last_activity_at"),
    )

    title: str
    owner_id: UUID = Field(index=True)
    last_activity_at: datetime = Field(sa_type=DateTime(timezone=True))

    messages: list["SessionMessageModel"] = Relationship(
        back_populates="session",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "order_by": "SessionMessageModel.position",
        },
    )
    playlist: "SessionPlaylistModel" = Relationship(
        back_populates="session",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "uselist": False,
        },
    )


class SessionMessageModel(DatabaseEntity, table=True):
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

    session: SessionModel = Relationship(back_populates="messages")


class SessionPlaylistModel(DatabaseEntity, table=True):
    __tablename__ = "session_playlists"

    session_id: UUID = Field(foreign_key="sessions.id", unique=True)
    name: str | None = None

    session: SessionModel = Relationship(back_populates="playlist")
    tracks: list["PlaylistTrackModel"] = Relationship(
        back_populates="playlist",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "order_by": "PlaylistTrackModel.position",
        },
    )


class PlaylistTrackModel(DatabaseEntity, table=True):
    __tablename__ = "playlist_tracks"

    playlist_id: UUID = Field(foreign_key="session_playlists.id")
    position: int
    title: str
    artist: str
    year: int | None = None
    cover_url: str | None = None

    playlist: SessionPlaylistModel = Relationship(back_populates="tracks")
