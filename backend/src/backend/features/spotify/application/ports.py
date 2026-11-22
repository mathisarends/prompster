from abc import ABC, abstractmethod

from backend.features.spotify.domain import (
    SpotifySearchType,
    SpotifyTrack,
    SpotifyUnifiedSearchResult,
)


class SpotifySearchGateway(ABC):
    @abstractmethod
    async def search(
        self,
        *,
        query: str,
        limit: int = 20,
        types: set[SpotifySearchType] | None = None,
        requester_id: str | None = None,
    ) -> SpotifyUnifiedSearchResult:
        raise NotImplementedError

    @abstractmethod
    async def get_track_by_id(self, *, track_id: str) -> SpotifyTrack | None:
        raise NotImplementedError


class SpotifyPlaylistCreator(ABC):
    @abstractmethod
    async def create_private_playlist(
        self,
        *,
        access_token: str,
        name: str,
        description: str,
    ) -> str:
        raise NotImplementedError

    @abstractmethod
    async def update_playlist_details(
        self,
        *,
        access_token: str,
        playlist_id: str,
        name: str,
        description: str,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def replace_playlist_tracks(
        self,
        *,
        access_token: str,
        playlist_id: str,
        track_uris: list[str],
    ) -> None:
        raise NotImplementedError
