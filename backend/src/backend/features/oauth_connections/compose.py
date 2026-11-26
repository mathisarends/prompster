from fastapi_canon import Feature

from backend.features.oauth_connections.infrastructure import OAuthConnectionsProvider
from backend.features.oauth_connections.presentation import (
    OAUTH_CONNECTION_ERRORS,
    spotify_oauth_router,
)

feature = Feature(
    name="oauth_connections",
    routers=[spotify_oauth_router],
    errors=OAUTH_CONNECTION_ERRORS,
    providers=[OAuthConnectionsProvider],
)
