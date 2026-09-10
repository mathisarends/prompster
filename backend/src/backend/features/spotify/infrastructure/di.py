from collections.abc import AsyncGenerator

from dishka import Provider, Scope, provide
from spotifyify import SpotifyCredentials, Spotifyify
from spotifyify.cache_handler import MemoryCacheHandler

import backend.features.spotify.infrastructure.spotify_playlist_creator as playlist_infra
import backend.features.spotify.infrastructure.spotify_search as spotify_search_infra
from backend.features.spotify.application.ports import (
    SpotifyPlaylistCreator,
    SpotifySearch,
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
    def provide_spotify_search_cache(self) -> SpotifySearchCache:
        return SpotifySearchCache()

    @provide(scope=Scope.APP)
    def provide_spotify_search(
        self,
        spotify: Spotifyify,
        search_cache: SpotifySearchCache,
    ) -> SpotifySearch:
        return spotify_search_infra.SpotifyifySearch(
            spotify=spotify,
            search_cache=search_cache,
        )

    @provide(scope=Scope.APP)
    def provide_spotify_playlist_creator(
        self,
        spotify: Spotifyify,
    ) -> SpotifyPlaylistCreator:
        return playlist_infra.SpotifyPlaylistCreator(spotify=spotify)
