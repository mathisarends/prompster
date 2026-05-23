from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PlaylistMetadataTrack:
    title: str
    artist: str
    year: int | None = None


@dataclass(frozen=True, slots=True)
class PlaylistMetadata:
    name: str
    description: str


class PlaylistMetadataGenerator(ABC):
    @abstractmethod
    async def generate(self, tracks: list[PlaylistMetadataTrack]) -> PlaylistMetadata:
        """Generates a meaningful playlist name and description from the tracks."""
