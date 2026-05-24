from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from backend.features.session.domain.exceptions import (
    PlaylistTrackNotFoundError,
    PlaylistTrackPinnedError,
    SessionAccessDeniedError,
    SessionExportRequiresSpotifyConnectionError,
    SessionPlaylistEmptyError,
    SessionPlaylistMissingSpotifyTracksError,
    SessionNotFoundError,
)


def _exception_detail(exc: Exception, *, fallback: str) -> str:
    detail = str(exc).strip()
    return detail if detail else fallback


async def _session_not_found_handler(
    _: Request,
    exc: SessionNotFoundError,
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": _exception_detail(exc, fallback="Session not found")},
    )


async def _session_access_denied_handler(
    _: Request,
    exc: SessionAccessDeniedError,
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content={"detail": _exception_detail(exc, fallback="Session access denied")},
    )


async def _playlist_track_not_found_handler(
    _: Request,
    exc: PlaylistTrackNotFoundError,
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": _exception_detail(exc, fallback="Playlist track not found")},
    )


async def _playlist_track_pinned_handler(
    _: Request,
    exc: PlaylistTrackPinnedError,
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": _exception_detail(exc, fallback="Playlist track is pinned")},
    )


async def _session_playlist_empty_handler(
    _: Request,
    exc: SessionPlaylistEmptyError,
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "detail": _exception_detail(exc, fallback="Session playlist is empty")
        },
    )


async def _session_playlist_missing_spotify_tracks_handler(
    _: Request,
    exc: SessionPlaylistMissingSpotifyTracksError,
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "detail": _exception_detail(
                exc,
                fallback="Session playlist has no tracks linked to Spotify",
            )
        },
    )


async def _session_export_requires_spotify_connection_handler(
    _: Request,
    exc: SessionExportRequiresSpotifyConnectionError,
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "detail": _exception_detail(
                exc,
                fallback="Spotify account is not connected",
            )
        },
    )


async def _bad_request_handler(_: Request, exc: ValueError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": _exception_detail(exc, fallback="Bad request")},
    )


def register_session_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(SessionNotFoundError, _session_not_found_handler)
    app.add_exception_handler(SessionAccessDeniedError, _session_access_denied_handler)
    app.add_exception_handler(
        PlaylistTrackNotFoundError, _playlist_track_not_found_handler
    )
    app.add_exception_handler(PlaylistTrackPinnedError, _playlist_track_pinned_handler)
    app.add_exception_handler(
        SessionPlaylistEmptyError, _session_playlist_empty_handler
    )
    app.add_exception_handler(
        SessionPlaylistMissingSpotifyTracksError,
        _session_playlist_missing_spotify_tracks_handler,
    )
    app.add_exception_handler(
        SessionExportRequiresSpotifyConnectionError,
        _session_export_requires_spotify_connection_handler,
    )
    app.add_exception_handler(ValueError, _bad_request_handler)
