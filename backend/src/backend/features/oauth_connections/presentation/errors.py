from fastapi import status
from fastapi_canon import Error

from backend.features.oauth_connections.application import (
    SpotifyConnectionNotFoundError,
    SpotifyTokenRevokedError,
)

SPOTIFY_CONNECTION_NOT_FOUND_ERROR = Error(
    SpotifyConnectionNotFoundError,
    status=status.HTTP_409_CONFLICT,
    code="spotify_connection_not_found",
    title="Spotify is not connected",
)
SPOTIFY_TOKEN_REVOKED_ERROR = Error(
    SpotifyTokenRevokedError,
    status=status.HTTP_410_GONE,
    code="spotify_token_revoked",
    title="Spotify access revoked",
)
