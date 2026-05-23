from collections.abc import AsyncGenerator

from dishka import Provider, Scope, provide
from spotifyify import SpotifyCredentials, Spotifyify
from spotifyify.cache_handler import MemoryCacheHandler

from backend.features.spotify.infrastructure.spotify_service import (
    SpotifyService,
)


class SpotifyProvider(Provider):
    @provide(scope=Scope.APP)
    def spotify_credentials(self) -> SpotifyCredentials:
        return SpotifyCredentials()

    @provide(scope=Scope.APP)
    async def spotify(
        self,
        credentials: SpotifyCredentials,
    ) -> AsyncGenerator[Spotifyify, None]:
        spotify = Spotifyify(
            credentials=credentials,
            cache_handler=MemoryCacheHandler(),
        )
        try:
            yield spotify
        finally:
            await spotify.close()

    @provide(scope=Scope.APP)
    def provide_spotify_service(
        self,
        spotify: Spotifyify,
    ) -> SpotifyService:
        return SpotifyService(spotify=spotify)
