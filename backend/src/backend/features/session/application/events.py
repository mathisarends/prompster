from dataclasses import dataclass
from uuid import UUID

from backend.features.session.domain import (
    AssistantMessage,
    FollowUpQuestionGroup,
    Playlist,
    PlaylistTrack,
    ToolCallGroup,
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
class SessionToolCallGroupAdded:
    group: ToolCallGroup


@dataclass(frozen=True)
class SessionToolCallResolved:
    group_id: UUID
    tool_call_id: str
    result: str


@dataclass(frozen=True)
class SessionToolCallFailed:
    group_id: UUID
    tool_call_id: str
    error: str


@dataclass(frozen=True)
class SessionToolCallGroupCompleted:
    group_id: UUID


@dataclass(frozen=True)
class SessionFollowUpGroupAdded:
    group: FollowUpQuestionGroup


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
    | SessionToolCallGroupAdded
    | SessionToolCallResolved
    | SessionToolCallFailed
    | SessionToolCallGroupCompleted
    | SessionFollowUpGroupAdded
    | SessionPlaylistSet
    | SessionPlaylistTrackAdded
    | SessionPlaylistTrackRemoved
)
