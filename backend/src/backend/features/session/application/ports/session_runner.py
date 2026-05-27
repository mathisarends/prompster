from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass
from uuid import UUID

from backend.features.session.domain import (
    FollowUpQuestion,
    PendingCall,
    Playlist,
    PlaylistTrack,
    Session,
)


@dataclass(frozen=True)
class SessionRunnerAssistantMessage:
    content: str


@dataclass(frozen=True)
class SessionRunnerAssistantMessageChunk:
    chunk: str


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


@dataclass(frozen=True)
class SessionRunnerPlaylistTracksAdded:
    playlist_id: UUID
    tracks: list[PlaylistTrack]


@dataclass(frozen=True)
class SessionRunnerPlaylistTracksRemoved:
    playlist_id: UUID
    track_ids: list[UUID]


@dataclass(frozen=True)
class SessionRunnerPlaylistTrackReplacement:
    track_id: UUID
    track: PlaylistTrack


@dataclass(frozen=True)
class SessionRunnerPlaylistTracksReplaced:
    playlist_id: UUID
    replacements: list[SessionRunnerPlaylistTrackReplacement]


@dataclass(frozen=True)
class SessionRunnerCancelled:
    pass


type SessionRunnerEvent = (
    SessionRunnerAssistantMessage
    | SessionRunnerAssistantMessageChunk
    | SessionRunnerToolCallStarted
    | SessionRunnerToolCallCompleted
    | SessionRunnerFollowUpRequested
    | SessionRunnerPlaylistUpdated
    | SessionRunnerPlaylistTracksAdded
    | SessionRunnerPlaylistTracksRemoved
    | SessionRunnerPlaylistTracksReplaced
    | SessionRunnerCancelled
)


class SessionRunner(ABC):
    @abstractmethod
    def run(self, *, session: Session) -> AsyncIterator[SessionRunnerEvent]:
        """Runs the agent with the session context and yields runner events."""

    async def stop(self, *, session_id: UUID) -> bool:
        """Requests a running session execution to stop."""
        return False
