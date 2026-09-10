from backend.features.auth.presentation.exception_handlers import AUTH_ERRORS
from backend.features.oauth_connections.application import (
    SpotifyConnectionNotFoundException,
    SpotifyTokenRevokedException,
)
from fastapi import status
from fastapi_canon import Error, ErrorRegistry

SPOTIFY_CONNECTION_NOT_FOUND_ERROR = Error(
    SpotifyConnectionNotFoundException,
    status=status.HTTP_409_CONFLICT,
    code="spotify_connection_not_found",
    title="Spotify is not connected",
)
SPOTIFY_TOKEN_REVOKED_ERROR = Error(
    SpotifyTokenRevokedException,
    status=status.HTTP_410_GONE,
    code="spotify_token_revoked",
    title="Spotify access revoked",
)

OAUTH_CONNECTION_ERRORS = ErrorRegistry.merge(
    AUTH_ERRORS,
    ErrorRegistry(
        name="oauth_connections_domain",
        errors=(SPOTIFY_CONNECTION_NOT_FOUND_ERROR, SPOTIFY_TOKEN_REVOKED_ERROR),
    ),
    name="oauth_connections",
)
