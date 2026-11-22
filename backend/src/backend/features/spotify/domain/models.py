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
    genres: tuple[str, ...]
    followers: int | None = None
    popularity: int | None = None
    image_url: str | None = None


@dataclass(frozen=True, slots=True)
class SpotifyUnifiedSearchResult:
    tracks: tuple[SpotifyTrack, ...]
    playlists: tuple[SpotifyPlaylist, ...]
    artists: tuple[SpotifyArtist, ...]
