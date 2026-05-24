from dataclasses import dataclass
from enum import StrEnum


class SpotifySearchType(StrEnum):
    TRACK = "track"
    PLAYLIST = "playlist"
    ARTIST = "artist"
    ALBUM = "album"


DEFAULT_SPOTIFY_SEARCH_TYPES = frozenset(
    {
        SpotifySearchType.TRACK,
        SpotifySearchType.PLAYLIST,
        SpotifySearchType.ARTIST,
        SpotifySearchType.ALBUM,
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
    preview_url: str | None = None


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
class SpotifyAlbum:
    id: str
    name: str
    artist: str
    year: int | None = None
    cover_url: str | None = None
    total_tracks: int | None = None


@dataclass(frozen=True, slots=True)
class SpotifyUnifiedSearchResult:
    tracks: list[SpotifyTrack]
    playlists: list[SpotifyPlaylist]
    artists: list[SpotifyArtist]
    albums: list[SpotifyAlbum]
