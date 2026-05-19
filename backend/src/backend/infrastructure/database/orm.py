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

    user_messages: list["SessionUserMessageModel"] = Relationship(
        back_populates="session",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    assistant_messages: list["SessionAssistantMessageModel"] = Relationship(
        back_populates="session",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    tool_call_groups: list["SessionToolCallGroupModel"] = Relationship(
        back_populates="session",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    follow_up_question_groups: list["SessionFollowUpQuestionGroupModel"] = Relationship(
        back_populates="session",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    playlist: "SessionPlaylistModel" = Relationship(
        back_populates="session",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "uselist": False,
        },
    )


class SessionUserMessageModel(DatabaseEntity, table=True):
    __tablename__ = "session_user_messages"
    __table_args__ = (
        Index("ix_session_user_messages_session_position", "session_id", "position"),
    )

    session_id: UUID = Field(foreign_key="sessions.id")
    position: int
    content: str

    session: SessionModel = Relationship(back_populates="user_messages")


class SessionAssistantMessageModel(DatabaseEntity, table=True):
    __tablename__ = "session_assistant_messages"
    __table_args__ = (
        Index(
            "ix_session_assistant_messages_session_position", "session_id", "position"
        ),
    )

    session_id: UUID = Field(foreign_key="sessions.id")
    position: int
    content: str

    session: SessionModel = Relationship(back_populates="assistant_messages")


class SessionToolCallGroupModel(DatabaseEntity, table=True):
    __tablename__ = "session_tool_call_groups"
    __table_args__ = (
        Index("ix_session_tool_call_groups_session_position", "session_id", "position"),
    )

    session_id: UUID = Field(foreign_key="sessions.id")
    position: int

    session: SessionModel = Relationship(back_populates="tool_call_groups")
    calls: list["SessionToolCallModel"] = Relationship(
        back_populates="group",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "order_by": "SessionToolCallModel.position",
        },
    )


class SessionToolCallModel(DatabaseEntity, table=True):
    __tablename__ = "session_tool_calls"

    group_id: UUID = Field(foreign_key="session_tool_call_groups.id")
    position: int
    call_id: str
    function_name: str
    function_arguments: dict[str, object] = Field(
        sa_column=Column(JSON, nullable=False)
    )
    state: str
    result: str | None = None
    error: str | None = None

    group: SessionToolCallGroupModel = Relationship(back_populates="calls")


class SessionFollowUpQuestionGroupModel(DatabaseEntity, table=True):
    __tablename__ = "session_follow_up_question_groups"
    __table_args__ = (
        Index(
            "ix_session_follow_up_question_groups_session_position",
            "session_id",
            "position",
        ),
    )

    session_id: UUID = Field(foreign_key="sessions.id")
    position: int

    session: SessionModel = Relationship(back_populates="follow_up_question_groups")
    questions: list["SessionFollowUpQuestionModel"] = Relationship(
        back_populates="group",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "order_by": "SessionFollowUpQuestionModel.position",
        },
    )


class SessionFollowUpQuestionModel(DatabaseEntity, table=True):
    __tablename__ = "session_follow_up_questions"

    group_id: UUID = Field(foreign_key="session_follow_up_question_groups.id")
    position: int
    question: str
    options: list[dict[str, object]] = Field(sa_column=Column(JSON, nullable=False))
    state: str
    answer_text: str | None = None
    answered_option_id: str | None = None

    group: SessionFollowUpQuestionGroupModel = Relationship(back_populates="questions")


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
