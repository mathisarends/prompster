from backend.presentation.feature import api_feature

from .infrastructure.di import OAuthConnectionsProvider
from .presentation import (
    OAUTH_CONNECTION_ERRORS,
    spotify_oauth_router,
)

feature = api_feature(
    routers=[spotify_oauth_router],
    providers=[OAuthConnectionsProvider],
    errors=OAUTH_CONNECTION_ERRORS,
)

__all__ = ["feature"]
