from collections.abc import AsyncGenerator

from dishka import Provider, Scope, provide
from spotifyify import SpotifyClient, SpotifyCredentials
from spotifyify.cache_handler import MemoryCacheHandler

import backend.features.spotify.infrastructure.spotify_playlist_creator as playlist_infra
import backend.features.spotify.infrastructure.spotify_search as SpotifyifySearch
from backend.features.spotify.application import (
    SpotifyPlaylistCreator,
    SpotifySearch,
    SpotifySearchGateway,
)
from backend.features.spotify.infrastructure.spotify_search_cache import (
    SpotifySearchCache,
)


class SpotifyProvider(Provider):
    @provide(scope=Scope.APP)
    def spotify_credentials(self) -> SpotifyCredentials:
        return SpotifyCredentials()

    @provide(scope=Scope.APP)
    async def spotify(
        self,
        credentials: SpotifyCredentials,
    ) -> AsyncGenerator[SpotifyClient]:
        spotify = SpotifyClient(
            credentials=credentials,
            cache_handler=MemoryCacheHandler(),
        )
        try:
            yield spotify
        finally:
            await spotify.aclose()

    @provide(scope=Scope.APP)
    def provide_spotify_search_cache(self) -> SpotifySearchCache:
        return SpotifySearchCache()

    @provide(scope=Scope.APP)
    def provide_spotify_search_gateway(
        self,
        spotify: SpotifyClient,
        search_cache: SpotifySearchCache,
    ) -> SpotifySearchGateway:
        return SpotifyifySearch(
            spotify=spotify,
            search_cache=search_cache,
        )

    @provide(scope=Scope.APP)
    def provide_spotify_search(
        self,
        gateway: SpotifySearchGateway,
    ) -> SpotifySearch:
        return SpotifySearch(gateway=gateway)

    @provide(scope=Scope.APP)
    def provide_spotify_playlist_creator(
        self,
        spotify: SpotifyClient,
    ) -> SpotifyPlaylistCreator:
        return playlist_infra.SpotifyPlaylistCreator(spotify=spotify)
