from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    LargeBinary,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
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
    profile_image_url: str | None = Field(default=None, sa_type=Text())


class AuthIdentityModel(DatabaseEntity, table=True):
    __tablename__ = "auth_identities"
    __table_args__ = (
        Index(
            "ix_auth_identities_provider_subject",
            "provider",
            "subject",
            unique=True,
        ),
        Index("ix_auth_identities_user_provider", "user_id", "provider", unique=True),
    )

    user_id: UUID = Field(foreign_key="users.id", ondelete="CASCADE", index=True)
    provider: str
    subject: str


class OAuthConnectionModel(DatabaseEntity, table=True):
    __tablename__ = "oauth_connections"
    __table_args__ = (
        Index("ix_oauth_connections_user_provider", "user_id", "provider", unique=True),
    )

    user_id: UUID = Field(foreign_key="users.id", ondelete="CASCADE")
    provider: str
    provider_user_id: str = Field(index=True)
    refresh_token_encrypted: bytes = Field(sa_type=LargeBinary())
    scope: str
    connected_at: datetime = Field(sa_type=DateTime(timezone=True))
    is_premium: bool = Field(
        default=False,
        sa_type=Boolean(),
        sa_column_kwargs={"server_default": text("false")},
    )


class SessionModel(DatabaseEntity, table=True):
    __tablename__ = "sessions"
    __table_args__ = (
        Index("ix_sessions_owner_id_last_activity_at", "owner_id", "last_activity_at"),
        Index(
            "ix_sessions_title_trgm",
            "title",
            postgresql_using="gin",
            postgresql_ops={"title": "gin_trgm_ops"},
        ),
    )

    title: str
    owner_id: UUID = Field(index=True)
    is_starred: bool = Field(
        default=False,
        sa_type=Boolean(),
        sa_column_kwargs={"server_default": text("false")},
    )
    phase: str = Field(
        default="onboarding",
        max_length=32,
        sa_column_kwargs={"server_default": text("'onboarding'")},
    )
    playlist_pdf_storage_key: str | None = Field(default=None, sa_type=Text())
    playlist_pdf_fingerprint: str | None = Field(default=None, max_length=64)
    last_activity_at: datetime = Field(sa_type=DateTime(timezone=True))

    user_messages: list["SessionUserMessageModel"] = Relationship(
        back_populates="session",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    assistant_messages: list["SessionAssistantMessageModel"] = Relationship(
        back_populates="session",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    user_curation_events: list["SessionUserCurationEventModel"] = Relationship(
        back_populates="session",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    playlist_references: list["SessionPlaylistReferenceModel"] = Relationship(
        back_populates="session",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    artist_references: list["SessionArtistReferenceModel"] = Relationship(
        back_populates="session",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    tool_call_sequences: list["SessionToolCallSequenceModel"] = Relationship(
        back_populates="session",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    onboarding_questions: list["SessionOnboardingQuestionModel"] = Relationship(
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


class ActiveSessionRunModel(SQLModel, table=True):
    __tablename__ = "active_session_runs"
    __table_args__ = (
        Index("ix_active_session_runs_run_id", "run_id"),
        Index("ix_active_session_runs_stop_requested", "stop_requested"),
    )

    session_id: UUID = Field(
        sa_column=Column(
            ForeignKey("sessions.id", ondelete="CASCADE"),
            primary_key=True,
            nullable=False,
        )
    )
    run_id: UUID
    stop_requested: bool = Field(
        default=False,
        sa_type=Boolean(),
        sa_column_kwargs={"server_default": text("false")},
    )
    created_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),
        sa_column_kwargs={"server_default": text("now()")},
    )
    updated_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),
        sa_column_kwargs={
            "server_default": text("now()"),
            "onupdate": text("now()"),
        },
    )
    stop_requested_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),
    )


class SessionAgentCheckpointModel(SQLModel, table=True):
    """The agent's harnessed session, saved as JSON to reopen it exactly.

    ``state`` is the settled history and changes only when history does;
    ``execution`` is the open turn on top of it and changes at every commit.
    """

    __tablename__ = "session_agent_checkpoints"

    session_id: UUID = Field(
        sa_column=Column(
            ForeignKey("sessions.id", ondelete="CASCADE"),
            primary_key=True,
            nullable=False,
        )
    )
    state: dict = Field(sa_column=Column(JSONB, nullable=False))
    execution: dict | None = Field(default=None, sa_column=Column(JSONB, nullable=True))
    updated_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),
        sa_column_kwargs={
            "server_default": text("now()"),
            "onupdate": text("now()"),
        },
    )


class SessionUserMessageModel(DatabaseEntity, table=True):
    __tablename__ = "session_user_messages"
    __table_args__ = (
        Index("ix_session_user_messages_session_position", "session_id", "position"),
    )

    session_id: UUID = Field(foreign_key="sessions.id", ondelete="CASCADE")
    position: int
    content: str = Field(sa_type=Text())

    session: SessionModel = Relationship(back_populates="user_messages")
    attachments: list["SessionUserMessageAttachmentModel"] = Relationship(
        back_populates="user_message",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "order_by": "SessionUserMessageAttachmentModel.position",
        },
    )
    image_attachments: list["SessionUserMessageImageAttachmentModel"] = Relationship(
        back_populates="user_message",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "order_by": "SessionUserMessageImageAttachmentModel.created_at",
        },
    )


class SessionUserMessageAttachmentModel(DatabaseEntity, table=True):
    __tablename__ = "session_user_message_attachments"
    __table_args__ = (
        Index(
            "ix_session_user_message_attachments_message_position",
            "user_message_id",
            "position",
        ),
    )

    user_message_id: UUID = Field(foreign_key="session_user_messages.id", ondelete="CASCADE")
    position: int
    kind: str = Field(max_length=64)
    external_id: str = Field(max_length=128)
    title: str = Field(sa_type=Text())
    subtitle: str | None = Field(default=None, sa_type=Text())
    image_url: str | None = Field(default=None, sa_type=Text())
    spotify_id: str | None = Field(default=None, max_length=128)

    user_message: SessionUserMessageModel = Relationship(back_populates="attachments")


class SessionUserMessageImageAttachmentModel(DatabaseEntity, table=True):
    __tablename__ = "session_user_message_image_attachments"
    __table_args__ = (
        Index(
            "ix_session_user_message_image_attachments_user_message_id",
            "user_message_id",
        ),
    )

    user_message_id: UUID = Field(
        sa_column=Column(
            ForeignKey("session_user_messages.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    storage_key: str = Field(sa_type=Text())
    content_type: str = Field(max_length=128)
    file_name: str = Field(sa_type=Text())
    size_bytes: int

    user_message: SessionUserMessageModel = Relationship(
        back_populates="image_attachments"
    )


class SessionAssistantMessageModel(DatabaseEntity, table=True):
    __tablename__ = "session_assistant_messages"
    __table_args__ = (
        Index(
            "ix_session_assistant_messages_session_position", "session_id", "position"
        ),
    )

    session_id: UUID = Field(foreign_key="sessions.id", ondelete="CASCADE")
    position: int
    content: str = Field(sa_type=Text())

    session: SessionModel = Relationship(back_populates="assistant_messages")


class SessionUserCurationEventModel(DatabaseEntity, table=True):
    __tablename__ = "session_user_curation_events"
    __table_args__ = (
        Index(
            "ix_session_user_curation_events_session_position",
            "session_id",
            "position",
        ),
        Index(
            "ix_session_user_curation_events_session_consumed",
            "session_id",
            "consumed",
        ),
    )

    session_id: UUID = Field(foreign_key="sessions.id", ondelete="CASCADE")
    position: int
    event_type: str
    track_id: UUID
    track_title: str = Field(sa_type=Text())
    track_artist: str = Field(sa_type=Text())
    track_year: int | None = None
    track_spotify_uri: str | None = Field(default=None, max_length=128)
    track_cover_url: str | None = Field(default=None, sa_type=Text())
    consumed: bool = Field(
        default=False,
        sa_type=Boolean(),
        sa_column_kwargs={"server_default": text("false")},
    )

    session: SessionModel = Relationship(back_populates="user_curation_events")


class SessionPlaylistReferenceModel(DatabaseEntity, table=True):
    __tablename__ = "session_playlist_references"
    __table_args__ = (
        UniqueConstraint(
            "session_id",
            "spotify_playlist_id",
            name="uq_session_playlist_references_session_spotify_playlist",
        ),
        Index(
            "ix_session_playlist_references_session_position",
            "session_id",
            "position",
        ),
    )

    session_id: UUID = Field(foreign_key="sessions.id", ondelete="CASCADE")
    position: int
    spotify_playlist_id: str = Field(max_length=64)
    name: str
    owner: str | None = None
    cover_url: str | None = None
    total_tracks: int | None = None

    session: SessionModel = Relationship(back_populates="playlist_references")


class SessionArtistReferenceModel(DatabaseEntity, table=True):
    __tablename__ = "session_artist_references"
    __table_args__ = (
        UniqueConstraint(
            "session_id",
            "spotify_artist_id",
            name="uq_session_artist_references_session_spotify_artist",
        ),
        Index(
            "ix_session_artist_references_session_position",
            "session_id",
            "position",
        ),
    )

    session_id: UUID = Field(foreign_key="sessions.id", ondelete="CASCADE")
    position: int
    spotify_artist_id: str = Field(max_length=64)
    name: str
    image_url: str | None = None
    genres: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSONB, nullable=False),
    )
    followers: int | None = None
    popularity: int | None = None

    session: SessionModel = Relationship(back_populates="artist_references")


class SessionToolCallSequenceModel(DatabaseEntity, table=True):
    __tablename__ = "session_tool_call_sequences"
    __table_args__ = (
        Index(
            "ix_session_tool_call_sequences_session_position",
            "session_id",
            "position",
        ),
    )

    session_id: UUID = Field(foreign_key="sessions.id", ondelete="CASCADE")
    position: int
    label: str | None = Field(default=None, sa_type=Text())

    session: SessionModel = Relationship(back_populates="tool_call_sequences")
    calls: list["SessionToolCallModel"] = Relationship(
        back_populates="sequence",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "order_by": "SessionToolCallModel.position",
        },
    )


class SessionToolCallModel(DatabaseEntity, table=True):
    __tablename__ = "session_tool_calls"

    sequence_id: UUID = Field(foreign_key="session_tool_call_sequences.id", ondelete="CASCADE")
    position: int
    call_id: str = Field(sa_type=Text())
    function_name: str = Field(sa_type=Text())
    function_arguments: dict[str, object] = Field(
        sa_column=Column(JSONB, nullable=False)
    )
    function_status_label: str | None = Field(default=None, sa_type=Text())
    function_action_type: str | None = Field(default=None, max_length=32)
    function_is_onboarding_question: bool = False
    state: str
    result: str | None = Field(default=None, sa_type=Text())
    error: str | None = Field(default=None, sa_type=Text())
    result_items: list[dict] | None = Field(
        default=None,
        sa_column=Column(JSON, nullable=True),
    )

    sequence: SessionToolCallSequenceModel = Relationship(back_populates="calls")


class SessionOnboardingQuestionModel(DatabaseEntity, table=True):
    __tablename__ = "session_onboarding_questions"
    __table_args__ = (
        Index(
            "ix_session_onboarding_questions_session_sequence",
            "session_id",
            "sequence_number",
        ),
    )

    session_id: UUID = Field(foreign_key="sessions.id", ondelete="CASCADE")
    sequence_number: int
    question_text: str
    hint: str | None = Field(default=None, sa_type=Text())
    options: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    recommended_option: str | None = None
    selection_mode: str = Field(
        default="single_select",
        max_length=32,
        sa_column_kwargs={"server_default": text("'single_select'")},
    )
    is_last_question: bool = Field(
        default=False,
        sa_type=Boolean(),
        sa_column_kwargs={"server_default": text("false")},
    )
    answer: str | None = None
    answers: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    is_answered: bool = Field(
        default=False,
        sa_type=Boolean(),
        sa_column_kwargs={"server_default": text("false")},
    )
    answered_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))

    session: SessionModel = Relationship(back_populates="onboarding_questions")


class SessionPlaylistModel(DatabaseEntity, table=True):
    __tablename__ = "session_playlists"

    session_id: UUID = Field(foreign_key="sessions.id", ondelete="CASCADE", unique=True)
    name: str | None = None
    spotify_playlist_id: str | None = Field(default=None, max_length=64)

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
    __table_args__ = (
        Index("ix_playlist_tracks_playlist_id_position", "playlist_id", "position"),
    )

    playlist_id: UUID = Field(foreign_key="session_playlists.id", ondelete="CASCADE")
    position: int
    title: str = Field(sa_type=Text())
    artist: str = Field(sa_type=Text())
    year: int
    spotify_uri: str | None = Field(default=None, max_length=128)
    cover_url: str | None = Field(default=None, sa_type=Text())

    playlist: SessionPlaylistModel = Relationship(back_populates="tracks")
