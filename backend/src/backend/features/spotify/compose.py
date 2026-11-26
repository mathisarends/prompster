from fastapi_canon import Feature

from backend.features.spotify.infrastructure import SpotifyProvider
from backend.features.spotify.presentation import spotify_router

feature = Feature(
    name="spotify",
    routers=[spotify_router],
    providers=[SpotifyProvider],
)
