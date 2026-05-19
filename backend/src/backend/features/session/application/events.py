from dataclasses import dataclass
from uuid import UUID

from backend.features.session.domain import (
    FollowUpQuestion,
    Playlist,
    PlaylistTrack,
    SessionMessage,
)


@dataclass(frozen=True)
class SessionTitleGenerated:
    session_id: UUID
    title: str


@dataclass(frozen=True)
class SessionUserMessageAppended:
    message: SessionMessage


@dataclass(frozen=True)
class SessionFollowUpAnswered:
    group_id: UUID
    question: FollowUpQuestion


@dataclass(frozen=True)
class SessionFollowUpSkipped:
    group_id: UUID
    question_id: UUID


@dataclass(frozen=True)
class SessionFollowUpGroupCompleted:
    group_id: UUID


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
    SessionTitleGenerated
    | SessionUserMessageAppended
    | SessionFollowUpAnswered
    | SessionFollowUpSkipped
    | SessionFollowUpGroupCompleted
    | SessionPlaylistSet
    | SessionPlaylistTrackAdded
    | SessionPlaylistTrackRemoved
)
