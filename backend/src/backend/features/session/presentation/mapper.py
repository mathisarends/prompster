from backend.features.session.application.ports.spotify_track_search import (
    SpotifyTrack,
)
from backend.features.session.domain import Session, SessionMessage
from backend.features.session.presentation.schemas import (
    MessageResponse,
    SessionResponse,
    SpotifyTrackResponse,
)


def to_session_response(session: Session) -> SessionResponse:
    return SessionResponse(
        id=session.id,
        title=session.title,
        created_at=session.created_at,
    )


def to_message_response(message: SessionMessage) -> MessageResponse:
    return MessageResponse(
        id=message.id,
        role=message.role,
        content=message.content,
        created_at=message.created_at,
    )


def to_spotify_track_response(track: SpotifyTrack) -> SpotifyTrackResponse:
    return SpotifyTrackResponse(
        id=track.id,
        title=track.title,
        artist=track.artist,
        album=track.album,
        year=track.year,
        cover_url=track.cover_url,
        preview_url=track.preview_url,
    )
