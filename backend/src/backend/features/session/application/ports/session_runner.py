from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from backend.features.session.domain import (
    OnboardingQuestionSelectionMode,
    PendingCall,
    Playlist,
    PlaylistTrack,
    Session,
    ToolResultItem,
)


class _RunnerEvent(BaseModel):
    # ``frozen`` keeps the value-object semantics of the previous frozen
    # dataclasses; ``arbitrary_types_allowed`` lets the events carry plain
    # domain objects (Entity-based ``Playlist``/``PlaylistTrack``) as-is
    # without pydantic trying to validate or coerce them.
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)


class SessionRunnerAssistantMessage(_RunnerEvent):
    content: str


class SessionRunnerAssistantMessageChunk(_RunnerEvent):
    chunk: str


class SessionRunnerToolCallStarted(_RunnerEvent):
    call: PendingCall


class SessionRunnerToolCallSequenceStarted(_RunnerEvent):
    label: str | None = None


class SessionRunnerToolCallCompleted(_RunnerEvent):
    tool_call_id: str
    result: str
    items: list[ToolResultItem] = Field(default_factory=list)


class SessionRunnerToolCallRetry(_RunnerEvent):
    tool_call_id: str
    name: str
    attempt: int
    max_attempts: int
    retry_in_seconds: float | None = None


class SessionRunnerPlaylistUpdated(_RunnerEvent):
    playlist: Playlist


class SessionRunnerPlaylistTracksAdded(_RunnerEvent):
    playlist_id: UUID
    tracks: list[PlaylistTrack]


class SessionRunnerPlaylistTracksRemoved(_RunnerEvent):
    playlist_id: UUID
    track_ids: list[UUID]


class SessionRunnerPlaylistTrackReplacement(_RunnerEvent):
    track_id: UUID
    track: PlaylistTrack


class SessionRunnerPlaylistTracksReplaced(_RunnerEvent):
    playlist_id: UUID
    replacements: list[SessionRunnerPlaylistTrackReplacement]


class SessionRunnerContextCompacted(_RunnerEvent):
    reason: str
    tokens_before: int | None = None
    compacted_tool_results: int = 0


class SessionRunnerCancelled(_RunnerEvent):
    pass


class SessionRunnerQuestionAsked(_RunnerEvent):
    question: str | None = None
    hint: str | None = None
    options: list[str] | None = None
    recommended_option: str | None = None
    selection_mode: OnboardingQuestionSelectionMode = (
        OnboardingQuestionSelectionMode.SINGLE_SELECT
    )


class SessionRunnerSuspendedForInput(_RunnerEvent):
    question: str | None = None
    hint: str | None = None
    options: list[str] | None = None
    recommended_option: str | None = None
    selection_mode: OnboardingQuestionSelectionMode = (
        OnboardingQuestionSelectionMode.SINGLE_SELECT
    )
    is_last_question: bool = False


type SessionRunnerEvent = (
    SessionRunnerAssistantMessage
    | SessionRunnerAssistantMessageChunk
    | SessionRunnerToolCallSequenceStarted
    | SessionRunnerToolCallStarted
    | SessionRunnerToolCallCompleted
    | SessionRunnerToolCallRetry
    | SessionRunnerPlaylistUpdated
    | SessionRunnerPlaylistTracksAdded
    | SessionRunnerPlaylistTracksRemoved
    | SessionRunnerPlaylistTracksReplaced
    | SessionRunnerContextCompacted
    | SessionRunnerCancelled
    | SessionRunnerQuestionAsked
    | SessionRunnerSuspendedForInput
)


class SessionRunner(ABC):
    @abstractmethod
    def run(
        self,
        *,
        session: Session,
        model_id: str | None = None,
    ) -> AsyncIterator[SessionRunnerEvent]:
        """Runs the agent with the session context and yields runner events."""

    async def stop(self, *, session_id: UUID) -> bool:
        """Requests a running session execution to stop."""
        return False
