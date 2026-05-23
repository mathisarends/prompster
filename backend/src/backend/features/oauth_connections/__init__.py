from backend.presentation.feature import Feature

from .infrastructure.di import OAuthConnectionsProvider
from .presentation import (
    register_oauth_connections_exception_handlers,
    spotify_oauth_router,
)

feature = Feature(
    name="oauth_connections",
    routers=[spotify_oauth_router],
    providers=[OAuthConnectionsProvider],
    register_exception_handlers=register_oauth_connections_exception_handlers,
)

__all__ = ["feature"]
