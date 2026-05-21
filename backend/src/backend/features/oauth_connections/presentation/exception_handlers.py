from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from backend.features.oauth_connections.application import (
    SpotifyConnectionNotFoundException,
    SpotifyTokenRevokedException,
)


async def _spotify_connection_not_found_handler(
    _: Request,
    __: SpotifyConnectionNotFoundException,
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": "Spotify is not connected"},
    )


async def _spotify_token_revoked_handler(
    _: Request,
    __: SpotifyTokenRevokedException,
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_410_GONE,
        content={"detail": "Spotify access revoked, please reconnect"},
    )


def register_oauth_connections_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(
        SpotifyConnectionNotFoundException,
        _spotify_connection_not_found_handler,
    )
    app.add_exception_handler(
        SpotifyTokenRevokedException,
        _spotify_token_revoked_handler,
    )
