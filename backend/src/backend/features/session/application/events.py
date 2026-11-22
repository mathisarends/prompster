from dataclasses import dataclass, field
from enum import StrEnum
from uuid import UUID

from backend.features.session.domain import (
    AssistantMessage,
    OnboardingQuestionSelectionMode,
    Playlist,
    PlaylistTrack,
    Session,
    ToolCallSequence,
    ToolResultItem,
)


class SuspensionKind(StrEnum):
    ONBOARDING_QUESTION = "onboarding_question"
    PLAYLIST_CONTEXT = "playlist_context"


@dataclass(frozen=True, slots=True)
class SessionSnapshot:
    session: Session


@dataclass(frozen=True, slots=True)
class SessionAssistantMessageStarted:
    message: AssistantMessage


@dataclass(frozen=True, slots=True)
class SessionAssistantMessageChunk:
    message_id: UUID
    chunk: str


@dataclass(frozen=True, slots=True)
class SessionAssistantMessageCompleted:
    message: AssistantMessage


@dataclass(frozen=True, slots=True)
class SessionAssistantMessageCancelled:
    message_id: UUID


@dataclass(frozen=True, slots=True)
class SessionToolCallSequenceAdded:
    sequence: ToolCallSequence


@dataclass(frozen=True, slots=True)
class SessionToolCallResolved:
    sequence_id: UUID
    tool_call_id: str
    result: str
    items: tuple[ToolResultItem, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class SessionToolCallFailed:
    sequence_id: UUID
    tool_call_id: str
    error: str


@dataclass(frozen=True, slots=True)
class SessionToolCallRetry:
    """A transient retry of a still-pending tool call's upstream request.

    Surfaced live for reassurance; never persisted and does not mutate the
    session. ``sequence_id`` is best-effort — it is ``None`` if no pending
    sequence is found (e.g. for skipped onboarding-question tool calls).
    """

    tool_call_id: str
    name: str
    attempt: int
    max_attempts: int
    retry_in_seconds: float | None = None
    sequence_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class SessionToolCallSequenceCompleted:
    sequence_id: UUID


@dataclass(frozen=True, slots=True)
class SessionPlaylistSet:
    playlist: Playlist


@dataclass(frozen=True, slots=True)
class SessionPlaylistTrackAdded:
    playlist_id: UUID
    track: PlaylistTrack


@dataclass(frozen=True, slots=True)
class SessionPlaylistTrackRemoved:
    playlist_id: UUID
    track_id: UUID


@dataclass(frozen=True, slots=True)
class SessionPlaylistTrackReplaced:
    playlist_id: UUID
    track_id: UUID
    track: PlaylistTrack


@dataclass(frozen=True, slots=True)
class SessionContextCompacted:
    """Older tool results were elided to stay under the model's token budget.

    Transient and informational: never persisted, never mutates the session.
    Surfaced so the UI can reassure the user that a long run is being trimmed
    rather than failing.
    """

    reason: str
    tokens_before: int | None = None
    compacted_tool_results: int = 0


@dataclass(frozen=True, slots=True)
class SessionTitleGenerated:
    title: str


@dataclass(frozen=True, slots=True)
class SessionOnboardingQuestionAsked:
    question: str
    options: list[str]
    hint: str | None = None
    recommended_option: str | None = None
    selection_mode: OnboardingQuestionSelectionMode = (
        OnboardingQuestionSelectionMode.SINGLE_SELECT
    )
    question_id: UUID | None = None
    is_last_question: bool = False


@dataclass(frozen=True, slots=True)
class SessionSuspendedForInput:
    kind: SuspensionKind
    question: str | None = None
    hint: str | None = None
    options: list[str] | None = None
    recommended_option: str | None = None
    selection_mode: OnboardingQuestionSelectionMode = (
        OnboardingQuestionSelectionMode.SINGLE_SELECT
    )
    question_id: UUID | None = None
    is_last_question: bool = False


type SessionEvent = (
    SessionSnapshot
    | SessionAssistantMessageStarted
    | SessionAssistantMessageChunk
    | SessionAssistantMessageCompleted
    | SessionAssistantMessageCancelled
    | SessionToolCallSequenceAdded
    | SessionToolCallResolved
    | SessionToolCallFailed
    | SessionToolCallRetry
    | SessionToolCallSequenceCompleted
    | SessionPlaylistSet
    | SessionPlaylistTrackAdded
    | SessionPlaylistTrackRemoved
    | SessionPlaylistTrackReplaced
    | SessionTitleGenerated
    | SessionContextCompacted
    | SessionOnboardingQuestionAsked
    | SessionSuspendedForInput
)
