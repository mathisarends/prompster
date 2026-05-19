from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PlaylistDeckTrack:
    title: str
    artist_names: str
    release_year: str
    spotify_url: str


class PlaylistDeckPdfRenderer(ABC):
    @abstractmethod
    async def render(self, *, tracks: list[PlaylistDeckTrack]) -> bytes:
        """Renders playlist cards into a printable PDF document."""
