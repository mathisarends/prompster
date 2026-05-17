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


class SpotifyTrackSearch(ABC):
    @abstractmethod
    async def search(self, *, query: str, limit: int = 20) -> list[SpotifyTrack]:
        """Searches Spotify tracks matching the given query."""
