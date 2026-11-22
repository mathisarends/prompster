from fastapi_canon import Feature

from .infrastructure.di import SpotifyProvider
from .presentation import spotify_router

feature = Feature(
    name="spotify",
    routers=[spotify_router],
    providers=[SpotifyProvider],
)

__all__ = ["feature"]
