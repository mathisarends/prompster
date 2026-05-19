from backend.features.session.application.ports.session_summary_query import (
    SessionSummary,
)
from backend.features.session.domain import (
    PlaylistTrack,
    Session,
    SessionMessage,
)
from backend.features.session.presentation.schemas import (
    MessageResponse,
    PlaylistTrackResponse,
    SessionResponse,
    SessionSummaryResponse,
)


def to_session_response(session: Session) -> SessionResponse:
    return SessionResponse(
        id=session.id,
        title=session.title,
        created_at=session.created_at,
        messages=[to_message_response(message) for message in session.messages],
    )


def to_message_response(message: SessionMessage) -> MessageResponse:
    return MessageResponse(
        id=message.id,
        role=message.role,
        content=message.content,
        created_at=message.created_at,
    )


def to_session_summary_response(session: SessionSummary) -> SessionSummaryResponse:
    return SessionSummaryResponse(
        id=session.id,
        title=session.title,
        created_at=session.created_at,
        last_activity_at=session.last_activity_at,
    )


def to_playlist_track_response(track: PlaylistTrack) -> PlaylistTrackResponse:
    return PlaylistTrackResponse(
        id=track.id,
        title=track.title,
        artist=track.artist,
        year=track.year,
        cover_url=track.cover_url,
    )
