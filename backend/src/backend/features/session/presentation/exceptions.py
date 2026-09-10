from backend.features.auth.presentation.exceptions import AUTH_ERRORS
from backend.features.session.application import InvalidImageAttachmentError
from backend.features.session.domain.exceptions import (
    ArtistReferenceNotFoundError,
    InvalidSessionPhaseTransitionError,
    NoCurrentAssistantMessageError,
    NoPendingToolCallSequenceError,
    PendingToolCallsError,
    PlaylistReferenceNotFoundError,
    PlaylistTrackLimitExceededError,
    PlaylistTrackNotFoundError,
    SessionAccessDeniedError,
    SessionExportRequiresSpotifyConnectionError,
    SessionNotFoundError,
    SessionPlaylistEmptyError,
    SessionPlaylistMissingSpotifyTracksError,
    ToolCallAlreadyResolvedError,
    ToolCallNotFoundError,
    UserCurationEventAlreadyConsumedError,
    UserCurationEventMissingTrackYearError,
    UserCurationEventNotFoundError,
)
from backend.features.spotify.application import (
    InvalidSpotifyTrackUriError,
    SpotifyTrackNotFoundError,
    SpotifyTrackYearMissingError,
)
from fastapi import status
from fastapi_canon import Error, ErrorRegistry

SESSION_NOT_FOUND_ERROR = Error(
    SessionNotFoundError,
    status=status.HTTP_404_NOT_FOUND,
    code="session_not_found",
    title="Session not found",
)
INVALID_IMAGE_ATTACHMENT_ERROR = Error(
    InvalidImageAttachmentError,
    status=status.HTTP_400_BAD_REQUEST,
    code="invalid_image_attachment",
    title="Invalid image attachment",
)
SESSION_ACCESS_DENIED_ERROR = Error(
    SessionAccessDeniedError,
    status=status.HTTP_403_FORBIDDEN,
    code="session_access_denied",
    title="Session access denied",
)
INVALID_SESSION_PHASE_TRANSITION_ERROR = Error(
    InvalidSessionPhaseTransitionError,
    status=status.HTTP_409_CONFLICT,
    code="invalid_session_phase_transition",
    title="Invalid session phase transition",
)
PLAYLIST_TRACK_NOT_FOUND_ERROR = Error(
    PlaylistTrackNotFoundError,
    status=status.HTTP_404_NOT_FOUND,
    code="playlist_track_not_found",
    title="Playlist track not found",
)
PLAYLIST_TRACK_LIMIT_EXCEEDED_ERROR = Error(
    PlaylistTrackLimitExceededError,
    status=status.HTTP_409_CONFLICT,
    code="playlist_track_limit_exceeded",
    title="Playlist track limit exceeded",
)
PLAYLIST_REFERENCE_NOT_FOUND_ERROR = Error(
    PlaylistReferenceNotFoundError,
    status=status.HTTP_404_NOT_FOUND,
    code="playlist_reference_not_found",
    title="Playlist reference not found",
)
ARTIST_REFERENCE_NOT_FOUND_ERROR = Error(
    ArtistReferenceNotFoundError,
    status=status.HTTP_404_NOT_FOUND,
    code="artist_reference_not_found",
    title="Artist reference not found",
)
SESSION_PLAYLIST_EMPTY_ERROR = Error(
    SessionPlaylistEmptyError,
    status=status.HTTP_400_BAD_REQUEST,
    code="session_playlist_empty",
    title="Session playlist is empty",
)
SESSION_PLAYLIST_MISSING_SPOTIFY_TRACKS_ERROR = Error(
    SessionPlaylistMissingSpotifyTracksError,
    status=status.HTTP_400_BAD_REQUEST,
    code="session_playlist_missing_spotify_tracks",
    title="Session playlist has no Spotify tracks",
)
SESSION_EXPORT_REQUIRES_SPOTIFY_CONNECTION_ERROR = Error(
    SessionExportRequiresSpotifyConnectionError,
    status=status.HTTP_409_CONFLICT,
    code="session_export_requires_spotify_connection",
    title="Spotify connection required",
)
TOOL_CALL_NOT_FOUND_ERROR = Error(
    ToolCallNotFoundError,
    status=status.HTTP_404_NOT_FOUND,
    code="tool_call_not_found",
    title="Tool call not found",
)
TOOL_CALL_ALREADY_RESOLVED_ERROR = Error(
    ToolCallAlreadyResolvedError,
    status=status.HTTP_409_CONFLICT,
    code="tool_call_already_resolved",
    title="Tool call already resolved",
)
NO_PENDING_TOOL_CALL_SEQUENCE_ERROR = Error(
    NoPendingToolCallSequenceError,
    status=status.HTTP_409_CONFLICT,
    code="no_pending_tool_call_sequence",
    title="No pending tool call sequence",
)
PENDING_TOOL_CALLS_ERROR = Error(
    PendingToolCallsError,
    status=status.HTTP_409_CONFLICT,
    code="pending_tool_calls",
    title="Pending tool calls exist",
)
NO_CURRENT_ASSISTANT_MESSAGE_ERROR = Error(
    NoCurrentAssistantMessageError,
    status=status.HTTP_409_CONFLICT,
    code="no_current_assistant_message",
    title="No current assistant message",
)
USER_CURATION_EVENT_NOT_FOUND_ERROR = Error(
    UserCurationEventNotFoundError,
    status=status.HTTP_404_NOT_FOUND,
    code="user_curation_event_not_found",
    title="Curation event not found",
)
USER_CURATION_EVENT_ALREADY_CONSUMED_ERROR = Error(
    UserCurationEventAlreadyConsumedError,
    status=status.HTTP_409_CONFLICT,
    code="user_curation_event_already_consumed",
    title="Curation event already consumed",
)
USER_CURATION_EVENT_MISSING_TRACK_YEAR_ERROR = Error(
    UserCurationEventMissingTrackYearError,
    status=status.HTTP_409_CONFLICT,
    code="user_curation_event_missing_track_year",
    title="Curation event track year missing",
)
INVALID_SPOTIFY_TRACK_URI_ERROR = Error(
    InvalidSpotifyTrackUriError,
    status=status.HTTP_400_BAD_REQUEST,
    code="invalid_spotify_track_uri",
    title="Invalid Spotify track URI",
)
SPOTIFY_TRACK_NOT_FOUND_ERROR = Error(
    SpotifyTrackNotFoundError,
    status=status.HTTP_404_NOT_FOUND,
    code="spotify_track_not_found",
    title="Spotify track not found",
)
SPOTIFY_TRACK_YEAR_MISSING_ERROR = Error(
    SpotifyTrackYearMissingError,
    status=status.HTTP_409_CONFLICT,
    code="spotify_track_year_missing",
    title="Spotify track release year missing",
)

SESSION_ERRORS = ErrorRegistry.merge(
    AUTH_ERRORS,
    ErrorRegistry(
        name="session_domain",
        errors=(
            SESSION_NOT_FOUND_ERROR,
            INVALID_IMAGE_ATTACHMENT_ERROR,
            SESSION_ACCESS_DENIED_ERROR,
            INVALID_SESSION_PHASE_TRANSITION_ERROR,
            PLAYLIST_TRACK_NOT_FOUND_ERROR,
            PLAYLIST_TRACK_LIMIT_EXCEEDED_ERROR,
            PLAYLIST_REFERENCE_NOT_FOUND_ERROR,
            ARTIST_REFERENCE_NOT_FOUND_ERROR,
            SESSION_PLAYLIST_EMPTY_ERROR,
            SESSION_PLAYLIST_MISSING_SPOTIFY_TRACKS_ERROR,
            SESSION_EXPORT_REQUIRES_SPOTIFY_CONNECTION_ERROR,
            TOOL_CALL_NOT_FOUND_ERROR,
            TOOL_CALL_ALREADY_RESOLVED_ERROR,
            NO_PENDING_TOOL_CALL_SEQUENCE_ERROR,
            PENDING_TOOL_CALLS_ERROR,
            NO_CURRENT_ASSISTANT_MESSAGE_ERROR,
            USER_CURATION_EVENT_NOT_FOUND_ERROR,
            USER_CURATION_EVENT_ALREADY_CONSUMED_ERROR,
            USER_CURATION_EVENT_MISSING_TRACK_YEAR_ERROR,
            INVALID_SPOTIFY_TRACK_URI_ERROR,
            SPOTIFY_TRACK_NOT_FOUND_ERROR,
            SPOTIFY_TRACK_YEAR_MISSING_ERROR,
        ),
    ),
    name="session",
)
