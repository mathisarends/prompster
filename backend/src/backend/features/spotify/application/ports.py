from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SpotifyTrack:
    id: str
    title: str
    artist: str
    album: str | None = None
    year: int | None = None
    cover_url: str | None = None
    preview_url: str | None = None


@dataclass(frozen=True, slots=True)
class SpotifyPlaylist:
    id: str
    name: str
    owner: str | None = None
    cover_url: str | None = None
    total_tracks: int | None = None


class SpotifyService(ABC):
    @abstractmethod
    async def search_tracks(
        self,
        *,
        query: str,
        limit: int = 20,
    ) -> list[SpotifyTrack]:
        """Searches Spotify tracks matching the given query."""

    @abstractmethod
    async def search_playlists(
        self,
        *,
        query: str,
        limit: int = 20,
    ) -> list[SpotifyPlaylist]:
        """Searches Spotify playlists matching the given query."""
