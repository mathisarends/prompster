from backend.presentation.feature import api_feature

from .infrastructure.di import SpotifyProvider
from .presentation import spotify_router

feature = api_feature(
    name="spotify",
    routers=[spotify_router],
    providers=[SpotifyProvider],
)

__all__ = ["feature"]
