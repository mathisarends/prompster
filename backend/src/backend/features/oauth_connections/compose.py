from fastapi_canon import Feature

from backend.features.oauth_connections.infrastructure import OAuthConnectionsProvider
from backend.features.oauth_connections.presentation import spotify_oauth_router

feature = Feature(
    name="oauth_connections",
    routers=[spotify_oauth_router],
    providers=[OAuthConnectionsProvider],
)
