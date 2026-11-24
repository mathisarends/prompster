from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field

from backend.features.session.domain import OnboardingQuestionSelectionMode, RunStatus
from backend.features.session.presentation.schemas import (
    AssistantMessageEntryResponse,
    PlaylistTrackResponse,
    SessionEntryResponse,
    ToolCallResultItemResponse,
    ToolCallSequenceEntryResponse,
)
from backend.presentation import Schema


class SessionStreamEventType(StrEnum):
    SESSION_SNAPSHOT = "session.snapshot"
    TITLE_GENERATED = "session.title_generated"

    ASSISTANT_MESSAGE_STARTED = "message.assistant_started"
    ASSISTANT_MESSAGE_CHUNK = "message.assistant_chunk"
    ASSISTANT_MESSAGE_COMPLETED = "message.assistant_completed"
    ASSISTANT_MESSAGE_CANCELLED = "message.assistant_cancelled"

    TOOL_CALL_SEQUENCE_ADDED = "tool_call.sequence_added"
    TOOL_CALL_RESOLVED = "tool_call.resolved"
    TOOL_CALL_FAILED = "tool_call.failed"
    TOOL_CALL_RETRY = "tool_call.retry"
    TOOL_CALL_SEQUENCE_COMPLETED = "tool_call.sequence_completed"

    CONTEXT_COMPACTED = "session.context_compacted"
    RUN_STATUS_CHANGED = "session.run_status_changed"

    PLAYLIST_SET = "playlist.set"
    PLAYLIST_TRACK_ADDED = "playlist.track_added"
    PLAYLIST_TRACK_REMOVED = "playlist.track_removed"
    PLAYLIST_TRACK_REPLACED = "playlist.track_replaced"
    ONBOARDING_QUESTION_ASKED = "session.onboarding_question_asked"
    SUSPENDED_FOR_INPUT = "session.suspended_for_input"

    DONE = "done"
    ERROR = "error"


class _SessionEventSchema(Schema):
    type: SessionStreamEventType


class PlaylistPayload(Schema):
    id: UUID
    name: str | None = None
    tracks: list[PlaylistTrackResponse]


class SessionSnapshotPayload(Schema):
    id: UUID
    title: str
    created_at: datetime
    entries: list[SessionEntryResponse]
    playlist: PlaylistPayload | None = None


class SessionSnapshotEvent(_SessionEventSchema):
    type: Literal[SessionStreamEventType.SESSION_SNAPSHOT] = (
        SessionStreamEventType.SESSION_SNAPSHOT
    )
    session: SessionSnapshotPayload


class TitleGeneratedEvent(_SessionEventSchema):
    type: Literal[SessionStreamEventType.TITLE_GENERATED] = (
        SessionStreamEventType.TITLE_GENERATED
    )
    title: str


class AssistantMessageStartedEvent(_SessionEventSchema):
    type: Literal[SessionStreamEventType.ASSISTANT_MESSAGE_STARTED] = (
        SessionStreamEventType.ASSISTANT_MESSAGE_STARTED
    )
    message_id: UUID
    created_at: datetime


class AssistantMessageChunkEvent(_SessionEventSchema):
    type: Literal[SessionStreamEventType.ASSISTANT_MESSAGE_CHUNK] = (
        SessionStreamEventType.ASSISTANT_MESSAGE_CHUNK
    )
    message_id: UUID
    chunk: str


class AssistantMessageCompletedEvent(_SessionEventSchema):
    type: Literal[SessionStreamEventType.ASSISTANT_MESSAGE_COMPLETED] = (
        SessionStreamEventType.ASSISTANT_MESSAGE_COMPLETED
    )
    message: AssistantMessageEntryResponse


class AssistantMessageCancelledEvent(_SessionEventSchema):
    type: Literal[SessionStreamEventType.ASSISTANT_MESSAGE_CANCELLED] = (
        SessionStreamEventType.ASSISTANT_MESSAGE_CANCELLED
    )
    message_id: UUID


class ToolCallSequenceAddedEvent(_SessionEventSchema):
    type: Literal[SessionStreamEventType.TOOL_CALL_SEQUENCE_ADDED] = (
        SessionStreamEventType.TOOL_CALL_SEQUENCE_ADDED
    )
    sequence: ToolCallSequenceEntryResponse


class ToolCallResolvedEvent(_SessionEventSchema):
    type: Literal[SessionStreamEventType.TOOL_CALL_RESOLVED] = (
        SessionStreamEventType.TOOL_CALL_RESOLVED
    )
    sequence_id: UUID
    tool_call_id: str
    result: str
    result_items: list[ToolCallResultItemResponse] = Field(default_factory=list)


class ToolCallFailedEvent(_SessionEventSchema):
    type: Literal[SessionStreamEventType.TOOL_CALL_FAILED] = (
        SessionStreamEventType.TOOL_CALL_FAILED
    )
    sequence_id: UUID
    tool_call_id: str
    error: str


class ToolCallRetryEvent(_SessionEventSchema):
    type: Literal[SessionStreamEventType.TOOL_CALL_RETRY] = (
        SessionStreamEventType.TOOL_CALL_RETRY
    )
    tool_call_id: str
    name: str
    attempt: int
    max_attempts: int
    retry_in_seconds: float | None = None
    sequence_id: UUID | None = None


class ToolCallSequenceCompletedEvent(_SessionEventSchema):
    type: Literal[SessionStreamEventType.TOOL_CALL_SEQUENCE_COMPLETED] = (
        SessionStreamEventType.TOOL_CALL_SEQUENCE_COMPLETED
    )
    sequence_id: UUID


class ContextCompactedEvent(_SessionEventSchema):
    type: Literal[SessionStreamEventType.CONTEXT_COMPACTED] = (
        SessionStreamEventType.CONTEXT_COMPACTED
    )
    tokens_before: int
    tokens_after: int


class RunStatusChangedEvent(_SessionEventSchema):
    type: Literal[SessionStreamEventType.RUN_STATUS_CHANGED] = (
        SessionStreamEventType.RUN_STATUS_CHANGED
    )
    status: RunStatus


class PlaylistSetEvent(_SessionEventSchema):
    type: Literal[SessionStreamEventType.PLAYLIST_SET] = (
        SessionStreamEventType.PLAYLIST_SET
    )
    playlist: PlaylistPayload


class PlaylistTrackAddedEvent(_SessionEventSchema):
    type: Literal[SessionStreamEventType.PLAYLIST_TRACK_ADDED] = (
        SessionStreamEventType.PLAYLIST_TRACK_ADDED
    )
    playlist_id: UUID
    track: PlaylistTrackResponse


class PlaylistTrackRemovedEvent(_SessionEventSchema):
    type: Literal[SessionStreamEventType.PLAYLIST_TRACK_REMOVED] = (
        SessionStreamEventType.PLAYLIST_TRACK_REMOVED
    )
    playlist_id: UUID
    track_id: UUID


class PlaylistTrackReplacedEvent(_SessionEventSchema):
    type: Literal[SessionStreamEventType.PLAYLIST_TRACK_REPLACED] = (
        SessionStreamEventType.PLAYLIST_TRACK_REPLACED
    )
    playlist_id: UUID
    track_id: UUID
    track: PlaylistTrackResponse


class SuspendedForInputEvent(_SessionEventSchema):
    type: Literal[SessionStreamEventType.SUSPENDED_FOR_INPUT] = (
        SessionStreamEventType.SUSPENDED_FOR_INPUT
    )
    kind: str
    question: str | None = None
    hint: str | None = None
    options: list[str] = Field(default_factory=list)
    recommended_option: str | None = None
    selection_mode: OnboardingQuestionSelectionMode = (
        OnboardingQuestionSelectionMode.SINGLE_SELECT
    )
    question_id: UUID | None = None
    is_last_question: bool = False


class OnboardingQuestionAskedEvent(_SessionEventSchema):
    type: Literal[SessionStreamEventType.ONBOARDING_QUESTION_ASKED] = (
        SessionStreamEventType.ONBOARDING_QUESTION_ASKED
    )
    question: str
    hint: str | None = None
    options: list[str] = Field(default_factory=list)
    recommended_option: str | None = None
    selection_mode: OnboardingQuestionSelectionMode = (
        OnboardingQuestionSelectionMode.SINGLE_SELECT
    )
    question_id: UUID | None = None
    is_last_question: bool = False


class DoneEvent(_SessionEventSchema):
    type: Literal[SessionStreamEventType.DONE] = SessionStreamEventType.DONE


class ErrorEvent(_SessionEventSchema):
    type: Literal[SessionStreamEventType.ERROR] = SessionStreamEventType.ERROR
    code: str
    message: str
    correlation_id: str | None = None


type SessionStreamEvent = Annotated[
    SessionSnapshotEvent
    | TitleGeneratedEvent
    | AssistantMessageStartedEvent
    | AssistantMessageChunkEvent
    | AssistantMessageCompletedEvent
    | AssistantMessageCancelledEvent
    | ToolCallSequenceAddedEvent
    | ToolCallResolvedEvent
    | ToolCallFailedEvent
    | ToolCallRetryEvent
    | ToolCallSequenceCompletedEvent
    | ContextCompactedEvent
    | RunStatusChangedEvent
    | PlaylistSetEvent
    | PlaylistTrackAddedEvent
    | PlaylistTrackRemovedEvent
    | PlaylistTrackReplacedEvent
    | OnboardingQuestionAskedEvent
    | SuspendedForInputEvent
    | DoneEvent
    | ErrorEvent,
    Field(discriminator="type"),
]
