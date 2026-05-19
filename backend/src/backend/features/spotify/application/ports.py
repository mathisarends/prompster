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


class SpotifyService(ABC):
    @abstractmethod
    async def search_tracks(
        self,
        *,
        query: str,
        limit: int = 20,
    ) -> list[SpotifyTrack]:
        """Searches Spotify tracks matching the given query."""
