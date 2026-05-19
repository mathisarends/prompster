from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal, Union
from uuid import UUID

from pydantic import Field

from backend.features.session.domain import (
    FollowUpQuestionState,
    MessageRole,
    ToolCallState,
)
from backend.presentation.schema import Schema


class _SessionEventSchema(Schema):
    pass


class SessionEventType(StrEnum):
    SESSION_SNAPSHOT = "session.snapshot"
    SESSION_TITLE_GENERATED = "session.title_generated"

    USER_MESSAGE_APPENDED = "message.user_appended"

    ASSISTANT_MESSAGE_STARTED = "message.assistant_started"
    ASSISTANT_MESSAGE_CHUNK = "message.assistant_chunk"
    ASSISTANT_MESSAGE_COMPLETED = "message.assistant_completed"
    ASSISTANT_MESSAGE_CANCELLED = "message.assistant_cancelled"

    TOOL_CALL_GROUP_ADDED = "tool_call.group_added"
    TOOL_CALL_RESOLVED = "tool_call.resolved"
    TOOL_CALL_FAILED = "tool_call.failed"
    TOOL_CALL_GROUP_COMPLETED = "tool_call.group_completed"

    FOLLOW_UP_GROUP_ADDED = "follow_up.group_added"
    FOLLOW_UP_ANSWERED = "follow_up.answered"
    FOLLOW_UP_SKIPPED = "follow_up.skipped"
    FOLLOW_UP_GROUP_COMPLETED = "follow_up.group_completed"

    PLAYLIST_SET = "playlist.set"
    PLAYLIST_TRACK_ADDED = "playlist.track_added"
    PLAYLIST_TRACK_REMOVED = "playlist.track_removed"

    DONE = "done"
    ERROR = "error"


class FollowUpOptionPayload(_SessionEventSchema):
    id: str
    label: str


class FollowUpQuestionPayload(_SessionEventSchema):
    id: UUID
    question: str
    options: list[FollowUpOptionPayload]
    state: FollowUpQuestionState
    answer_text: str | None = None
    answered_option_id: str | None = None


class FollowUpQuestionGroupPayload(_SessionEventSchema):
    id: UUID
    questions: list[FollowUpQuestionPayload]


class ToolFunctionPayload(_SessionEventSchema):
    name: str
    arguments: dict[str, object]


class ToolCallPayload(_SessionEventSchema):
    id: str
    function: ToolFunctionPayload
    state: ToolCallState
    result: str | None = None
    error: str | None = None


class ToolCallGroupPayload(_SessionEventSchema):
    id: UUID
    calls: list[ToolCallPayload]


class PlaylistTrackPayload(_SessionEventSchema):
    id: UUID
    title: str
    artist: str
    year: int | None = None
    cover_url: str | None = None


class PlaylistPayload(_SessionEventSchema):
    id: UUID
    name: str | None = None
    tracks: list[PlaylistTrackPayload]


class MessagePayload(_SessionEventSchema):
    id: UUID
    role: MessageRole
    content: str
    created_at: datetime
    tool_call_group: ToolCallGroupPayload | None = None
    follow_up_group: FollowUpQuestionGroupPayload | None = None


class SessionSnapshotPayload(_SessionEventSchema):
    id: UUID
    title: str
    created_at: datetime
    messages: list[MessagePayload]
    playlist: PlaylistPayload | None = None


class SessionSnapshotEvent(_SessionEventSchema):
    type: Literal[SessionEventType.SESSION_SNAPSHOT] = SessionEventType.SESSION_SNAPSHOT
    session: SessionSnapshotPayload


class SessionTitleGeneratedEvent(_SessionEventSchema):
    type: Literal[SessionEventType.SESSION_TITLE_GENERATED] = (
        SessionEventType.SESSION_TITLE_GENERATED
    )
    session_id: UUID
    title: str


class UserMessageAppendedEvent(_SessionEventSchema):
    type: Literal[SessionEventType.USER_MESSAGE_APPENDED] = (
        SessionEventType.USER_MESSAGE_APPENDED
    )
    message: MessagePayload


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
    message: MessagePayload


class AssistantMessageCancelledEvent(_SessionEventSchema):
    type: Literal[SessionEventType.ASSISTANT_MESSAGE_CANCELLED] = (
        SessionEventType.ASSISTANT_MESSAGE_CANCELLED
    )
    message_id: UUID


class ToolCallGroupAddedEvent(_SessionEventSchema):
    type: Literal[SessionEventType.TOOL_CALL_GROUP_ADDED] = (
        SessionEventType.TOOL_CALL_GROUP_ADDED
    )
    message_id: UUID
    group: ToolCallGroupPayload


class ToolCallResolvedEvent(_SessionEventSchema):
    type: Literal[SessionEventType.TOOL_CALL_RESOLVED] = (
        SessionEventType.TOOL_CALL_RESOLVED
    )
    group_id: UUID
    tool_call_id: str
    result: str


class ToolCallFailedEvent(_SessionEventSchema):
    type: Literal[SessionEventType.TOOL_CALL_FAILED] = SessionEventType.TOOL_CALL_FAILED
    group_id: UUID
    tool_call_id: str
    error: str


class ToolCallGroupCompletedEvent(_SessionEventSchema):
    type: Literal[SessionEventType.TOOL_CALL_GROUP_COMPLETED] = (
        SessionEventType.TOOL_CALL_GROUP_COMPLETED
    )
    group_id: UUID


class FollowUpGroupAddedEvent(_SessionEventSchema):
    type: Literal[SessionEventType.FOLLOW_UP_GROUP_ADDED] = (
        SessionEventType.FOLLOW_UP_GROUP_ADDED
    )
    message_id: UUID
    group: FollowUpQuestionGroupPayload


class FollowUpAnsweredEvent(_SessionEventSchema):
    type: Literal[SessionEventType.FOLLOW_UP_ANSWERED] = (
        SessionEventType.FOLLOW_UP_ANSWERED
    )
    group_id: UUID
    question_id: UUID
    answer_text: str
    answered_option_id: str | None = None


class FollowUpSkippedEvent(_SessionEventSchema):
    type: Literal[SessionEventType.FOLLOW_UP_SKIPPED] = (
        SessionEventType.FOLLOW_UP_SKIPPED
    )
    group_id: UUID
    question_id: UUID


class FollowUpGroupCompletedEvent(_SessionEventSchema):
    type: Literal[SessionEventType.FOLLOW_UP_GROUP_COMPLETED] = (
        SessionEventType.FOLLOW_UP_GROUP_COMPLETED
    )
    group_id: UUID


class PlaylistSetEvent(_SessionEventSchema):
    type: Literal[SessionEventType.PLAYLIST_SET] = SessionEventType.PLAYLIST_SET
    playlist: PlaylistPayload


class PlaylistTrackAddedEvent(_SessionEventSchema):
    type: Literal[SessionEventType.PLAYLIST_TRACK_ADDED] = (
        SessionEventType.PLAYLIST_TRACK_ADDED
    )
    playlist_id: UUID
    track: PlaylistTrackPayload


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
        SessionTitleGeneratedEvent,
        UserMessageAppendedEvent,
        AssistantMessageStartedEvent,
        AssistantMessageChunkEvent,
        AssistantMessageCompletedEvent,
        AssistantMessageCancelledEvent,
        ToolCallGroupAddedEvent,
        ToolCallResolvedEvent,
        ToolCallFailedEvent,
        ToolCallGroupCompletedEvent,
        FollowUpGroupAddedEvent,
        FollowUpAnsweredEvent,
        FollowUpSkippedEvent,
        FollowUpGroupCompletedEvent,
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
