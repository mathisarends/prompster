from dataclasses import dataclass
from uuid import UUID

from backend.features.session.domain import (
    AssistantMessage,
    Playlist,
    PlaylistTrack,
)


@dataclass(frozen=True)
class SessionAssistantMessageStarted:
    message: AssistantMessage


@dataclass(frozen=True)
class SessionAssistantMessageChunk:
    message_id: UUID
    chunk: str


@dataclass(frozen=True)
class SessionAssistantMessageCompleted:
    message: AssistantMessage


@dataclass(frozen=True)
class SessionPlaylistSet:
    playlist: Playlist


@dataclass(frozen=True)
class SessionPlaylistTrackAdded:
    playlist_id: UUID
    track: PlaylistTrack


@dataclass(frozen=True)
class SessionPlaylistTrackRemoved:
    playlist_id: UUID
    track_id: UUID


type SessionEvent = (
    SessionAssistantMessageStarted
    | SessionAssistantMessageChunk
    | SessionAssistantMessageCompleted
    | SessionPlaylistSet
    | SessionPlaylistTrackAdded
    | SessionPlaylistTrackRemoved
)
