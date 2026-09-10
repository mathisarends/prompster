from backend.presentation.feature import api_feature

from .infrastructure.di import OAuthConnectionsProvider
from .presentation import spotify_oauth_router

feature = api_feature(
    name="oauth_connections",
    routers=[spotify_oauth_router],
    providers=[OAuthConnectionsProvider],
)

__all__ = ["feature"]
