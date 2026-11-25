from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PlaylistDeckTrack:
    title: str
    artist_names: str
    release_year: str
    spotify_url: str
    cover_url: str | None = None


class PlaylistDeckGenerator(ABC):
    @abstractmethod
    async def generate(
        self,
        tracks: list[PlaylistDeckTrack],
        *,
        page_limit: int | None = None,
    ) -> bytes:
        """Generates a playlist deck document from tracks."""
