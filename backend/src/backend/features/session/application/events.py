from dataclasses import dataclass
from uuid import UUID

from backend.features.session.domain import (
    AssistantMessage,
    FollowUpQuestionGroup,
    Playlist,
    PlaylistTrack,
    ToolCallSequence,
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
class SessionAssistantMessageCancelled:
    message_id: UUID


@dataclass(frozen=True)
class SessionToolCallSequenceAdded:
    sequence: ToolCallSequence


@dataclass(frozen=True)
class SessionToolCallResolved:
    sequence_id: UUID
    tool_call_id: str
    result: str


@dataclass(frozen=True)
class SessionToolCallFailed:
    sequence_id: UUID
    tool_call_id: str
    error: str


@dataclass(frozen=True)
class SessionToolCallSequenceCompleted:
    sequence_id: UUID


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


@dataclass(frozen=True)
class SessionPlaylistTrackReplaced:
    playlist_id: UUID
    track_id: UUID
    track: PlaylistTrack


@dataclass(frozen=True)
class SessionTitleGenerated:
    title: str


type SessionEvent = (
    SessionAssistantMessageStarted
    | SessionAssistantMessageChunk
    | SessionAssistantMessageCompleted
    | SessionAssistantMessageCancelled
    | SessionToolCallSequenceAdded
    | SessionToolCallResolved
    | SessionToolCallFailed
    | SessionToolCallSequenceCompleted
    | SessionFollowUpGroupAdded
    | SessionPlaylistSet
    | SessionPlaylistTrackAdded
    | SessionPlaylistTrackRemoved
    | SessionPlaylistTrackReplaced
    | SessionTitleGenerated
)
