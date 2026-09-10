from backend.presentation.feature import api_feature

from .infrastructure.di import SpotifyProvider
from .presentation import SPOTIFY_ERRORS, spotify_router

feature = api_feature(
    name="spotify",
    routers=[spotify_router],
    providers=[SpotifyProvider],
    errors=SPOTIFY_ERRORS,
)

__all__ = ["feature"]
