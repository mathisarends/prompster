from backend.features.session.application import (
    SessionAssistantMessageChunk,
    SessionAssistantMessageCompleted,
    SessionAssistantMessageStarted,
    SessionEvent,
    SessionPlaylistSet,
    SessionPlaylistTrackAdded,
    SessionPlaylistTrackRemoved,
)
from backend.features.session.domain import Playlist
from backend.features.session.presentation.mapper import (
    to_playlist_track_response,
)
from backend.features.session.presentation.schemas import (
    AssistantMessageEntryResponse,
)
from backend.features.session.presentation.sse.events import (
    AssistantMessageChunkEvent,
    AssistantMessageCompletedEvent,
    AssistantMessageStartedEvent,
    PlaylistPayload,
    PlaylistSetEvent,
    PlaylistTrackAddedEvent,
    PlaylistTrackRemovedEvent,
    ServerEvent,
)


def to_server_event(event: SessionEvent) -> ServerEvent:
    if isinstance(event, SessionAssistantMessageStarted):
        return AssistantMessageStartedEvent(
            message_id=event.message.id,
            created_at=event.message.created_at,
        )

    if isinstance(event, SessionAssistantMessageChunk):
        return AssistantMessageChunkEvent(
            message_id=event.message_id,
            chunk=event.chunk,
        )

    if isinstance(event, SessionAssistantMessageCompleted):
        return AssistantMessageCompletedEvent(
            message=AssistantMessageEntryResponse(
                id=event.message.id,
                content=event.message.content,
                created_at=event.message.created_at,
            ),
        )

    if isinstance(event, SessionPlaylistSet):
        return PlaylistSetEvent(playlist=_to_playlist_payload(event.playlist))

    if isinstance(event, SessionPlaylistTrackAdded):
        return PlaylistTrackAddedEvent(
            playlist_id=event.playlist_id,
            track=to_playlist_track_response(event.track),
        )

    if isinstance(event, SessionPlaylistTrackRemoved):
        return PlaylistTrackRemovedEvent(
            playlist_id=event.playlist_id,
            track_id=event.track_id,
        )

    raise TypeError(f"Unsupported session event: {type(event).__name__}")


def _to_playlist_payload(playlist: Playlist) -> PlaylistPayload:
    return PlaylistPayload(
        id=playlist.id,
        name=playlist.name,
        tracks=[to_playlist_track_response(track) for track in playlist.tracks],
    )
