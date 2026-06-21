from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import StrEnum


class SpotifySearchType(StrEnum):
    TRACK = "track"
    PLAYLIST = "playlist"
    ARTIST = "artist"


DEFAULT_SPOTIFY_SEARCH_TYPES = frozenset(
    {
        SpotifySearchType.TRACK,
        SpotifySearchType.PLAYLIST,
        SpotifySearchType.ARTIST,
    }
)


@dataclass(frozen=True, slots=True)
class SpotifyTrack:
    id: str
    title: str
    artist: str
    album: str | None = None
    year: int | None = None
    cover_url: str | None = None
    url: str | None = None


@dataclass(frozen=True, slots=True)
class SpotifyPlaylist:
    id: str
    name: str
    owner: str | None = None
    cover_url: str | None = None
    total_tracks: int | None = None


@dataclass(frozen=True, slots=True)
class SpotifyArtist:
    id: str
    name: str
    genres: list[str]
    followers: int | None = None
    popularity: int | None = None
    image_url: str | None = None


@dataclass(frozen=True, slots=True)
class SpotifyUnifiedSearchResult:
    tracks: list[SpotifyTrack]
    playlists: list[SpotifyPlaylist]
    artists: list[SpotifyArtist]


class SpotifySearch(ABC):
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
    async def get_track(self, *, track_id: str) -> SpotifyTrack | None:
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
