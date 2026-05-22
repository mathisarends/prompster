from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal, Union
from uuid import UUID

from pydantic import Field

from backend.features.session.presentation.schemas import (
    AssistantMessageEntryResponse,
    FollowUpQuestionGroupEntryResponse,
    PlaylistTrackResponse,
    SessionEntryResponse,
    ToolCallSequenceEntryResponse,
)
from backend.presentation.schema import Schema


class _SessionEventSchema(Schema):
    pass


class SessionEventType(StrEnum):
    SESSION_SNAPSHOT = "session.snapshot"

    ASSISTANT_MESSAGE_STARTED = "message.assistant_started"
    ASSISTANT_MESSAGE_CHUNK = "message.assistant_chunk"
    ASSISTANT_MESSAGE_COMPLETED = "message.assistant_completed"
    ASSISTANT_MESSAGE_CANCELLED = "message.assistant_cancelled"

    TOOL_CALL_SEQUENCE_ADDED = "tool_call.sequence_added"
    TOOL_CALL_RESOLVED = "tool_call.resolved"
    TOOL_CALL_FAILED = "tool_call.failed"
    TOOL_CALL_SEQUENCE_COMPLETED = "tool_call.sequence_completed"

    FOLLOW_UP_GROUP_ADDED = "follow_up.group_added"

    PLAYLIST_SET = "playlist.set"
    PLAYLIST_TRACK_ADDED = "playlist.track_added"
    PLAYLIST_TRACK_REMOVED = "playlist.track_removed"

    DONE = "done"
    ERROR = "error"


class PlaylistPayload(_SessionEventSchema):
    id: UUID
    name: str | None = None
    tracks: list[PlaylistTrackResponse]


class SessionSnapshotPayload(_SessionEventSchema):
    id: UUID
    title: str
    created_at: datetime
    entries: list[SessionEntryResponse]
    playlist: PlaylistPayload | None = None


class SessionSnapshotEvent(_SessionEventSchema):
    type: Literal[SessionEventType.SESSION_SNAPSHOT] = SessionEventType.SESSION_SNAPSHOT
    session: SessionSnapshotPayload


class AssistantMessageStartedEvent(_SessionEventSchema):
    type: Literal[SessionEventType.ASSISTANT_MESSAGE_STARTED] = (
        SessionEventType.ASSISTANT_MESSAGE_STARTED
    )
    message_id: UUID
    created_at: datetime


class AssistantMessageChunkEvent(_SessionEventSchema):
    type: Literal[SessionEventType.ASSISTANT_MESSAGE_CHUNK] = (
        SessionEventType.ASSISTANT_MESSAGE_CHUNK
    )
    message_id: UUID
    chunk: str


class AssistantMessageCompletedEvent(_SessionEventSchema):
    type: Literal[SessionEventType.ASSISTANT_MESSAGE_COMPLETED] = (
        SessionEventType.ASSISTANT_MESSAGE_COMPLETED
    )
    message: AssistantMessageEntryResponse


class AssistantMessageCancelledEvent(_SessionEventSchema):
    type: Literal[SessionEventType.ASSISTANT_MESSAGE_CANCELLED] = (
        SessionEventType.ASSISTANT_MESSAGE_CANCELLED
    )
    message_id: UUID


class ToolCallSequenceAddedEvent(_SessionEventSchema):
    type: Literal[SessionEventType.TOOL_CALL_SEQUENCE_ADDED] = (
        SessionEventType.TOOL_CALL_SEQUENCE_ADDED
    )
    sequence: ToolCallSequenceEntryResponse


class ToolCallResolvedEvent(_SessionEventSchema):
    type: Literal[SessionEventType.TOOL_CALL_RESOLVED] = (
        SessionEventType.TOOL_CALL_RESOLVED
    )
    sequence_id: UUID
    tool_call_id: str
    result: str


class ToolCallFailedEvent(_SessionEventSchema):
    type: Literal[SessionEventType.TOOL_CALL_FAILED] = SessionEventType.TOOL_CALL_FAILED
    sequence_id: UUID
    tool_call_id: str
    error: str


class ToolCallSequenceCompletedEvent(_SessionEventSchema):
    type: Literal[SessionEventType.TOOL_CALL_SEQUENCE_COMPLETED] = (
        SessionEventType.TOOL_CALL_SEQUENCE_COMPLETED
    )
    sequence_id: UUID


class FollowUpGroupAddedEvent(_SessionEventSchema):
    type: Literal[SessionEventType.FOLLOW_UP_GROUP_ADDED] = (
        SessionEventType.FOLLOW_UP_GROUP_ADDED
    )
    group: FollowUpQuestionGroupEntryResponse


class PlaylistSetEvent(_SessionEventSchema):
    type: Literal[SessionEventType.PLAYLIST_SET] = SessionEventType.PLAYLIST_SET
    playlist: PlaylistPayload


class PlaylistTrackAddedEvent(_SessionEventSchema):
    type: Literal[SessionEventType.PLAYLIST_TRACK_ADDED] = (
        SessionEventType.PLAYLIST_TRACK_ADDED
    )
    playlist_id: UUID
    track: PlaylistTrackResponse


class PlaylistTrackRemovedEvent(_SessionEventSchema):
    type: Literal[SessionEventType.PLAYLIST_TRACK_REMOVED] = (
        SessionEventType.PLAYLIST_TRACK_REMOVED
    )
    playlist_id: UUID
    track_id: UUID


class DoneEvent(_SessionEventSchema):
    type: Literal[SessionEventType.DONE] = SessionEventType.DONE


class ErrorEvent(_SessionEventSchema):
    type: Literal[SessionEventType.ERROR] = SessionEventType.ERROR
    code: str
    message: str
    correlation_id: str | None = None


ServerEvent = Annotated[
    Union[
        SessionSnapshotEvent,
        AssistantMessageStartedEvent,
        AssistantMessageChunkEvent,
        AssistantMessageCompletedEvent,
        AssistantMessageCancelledEvent,
        ToolCallSequenceAddedEvent,
        ToolCallResolvedEvent,
        ToolCallFailedEvent,
        ToolCallSequenceCompletedEvent,
        FollowUpGroupAddedEvent,
        PlaylistSetEvent,
        PlaylistTrackAddedEvent,
        PlaylistTrackRemovedEvent,
        DoneEvent,
        ErrorEvent,
    ],
    Field(discriminator="type"),
]


class SessionEventSchema(Schema):
    """References every server event shape for OpenAPI client generation."""

    server_event: ServerEvent | None = Field(
        default=None,
        description="Any event the backend may push over the stream.",
    )
