from fastapi_canon import Feature

from .infrastructure.di import OAuthConnectionsProvider
from .presentation import OAUTH_CONNECTION_ERRORS, spotify_oauth_router

feature = Feature(
    name="oauth_connections",
    routers=[spotify_oauth_router],
    errors=OAUTH_CONNECTION_ERRORS,
    providers=[OAuthConnectionsProvider],
)

__all__ = ["feature"]
