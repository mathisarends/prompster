from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PlaylistDeckTrack:
    title: str
    artist_names: str
    release_year: str
    spotify_url: str


class PlaylistDeckGenerator(ABC):
    @abstractmethod
    async def generate(self, tracks: list[PlaylistDeckTrack]) -> bytes:
        """Generates a playlist deck document from tracks."""
