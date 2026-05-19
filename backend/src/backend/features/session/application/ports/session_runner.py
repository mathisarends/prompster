from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass

from backend.features.session.domain import (
    FollowUpQuestion,
    PendingCall,
    Playlist,
    Session,
)


@dataclass(frozen=True)
class SessionRunnerAssistantMessage:
    content: str


@dataclass(frozen=True)
class SessionRunnerToolCallStarted:
    call: PendingCall


@dataclass(frozen=True)
class SessionRunnerToolCallCompleted:
    tool_call_id: str
    result: str


@dataclass(frozen=True)
class SessionRunnerFollowUpRequested:
    questions: list[FollowUpQuestion]


@dataclass(frozen=True)
class SessionRunnerPlaylistUpdated:
    playlist: Playlist


type SessionRunnerEvent = (
    SessionRunnerAssistantMessage
    | SessionRunnerToolCallStarted
    | SessionRunnerToolCallCompleted
    | SessionRunnerFollowUpRequested
    | SessionRunnerPlaylistUpdated
)


class SessionRunner(ABC):
    @abstractmethod
    def run(self, *, session: Session) -> AsyncIterator[SessionRunnerEvent]:
        """Runs the agent with the session context and yields runner events."""
