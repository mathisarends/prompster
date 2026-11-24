import asyncio
import logging
from collections.abc import AsyncGenerator, AsyncIterator, Callable, Iterator
from contextlib import aclosing, contextmanager
from dataclasses import dataclass
from typing import Self, cast

from spotifyify import (
    Image,
    OnRetryHook,
    PagingPlaylistTrack,
    Playlist,
    SimplifiedArtist,
    SimplifiedPlaylist,
    SpotifyClient,
    Track,
)
from spotifyify.cache_handler import MemoryCacheHandler
from spotifyify.validation import spotify_id

from agent.markup import release_label, tag
from agent.research.events import FoundPlaylist, FoundTrack

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class TrackResults:
    """What the model reads, and the tracks it can add from it."""

    content: str
    tracks: tuple[FoundTrack, ...]


@dataclass(frozen=True, slots=True)
class PlaylistResults:
    content: str
    playlists: tuple[FoundPlaylist, ...]


class Spotify:
    """Read-only Spotify research, rendered for the model."""

    def __init__(self, client: SpotifyClient | None = None) -> None:
        self._owns_client = client is None
        self._client = (
            client
            if client is not None
            else SpotifyClient(scopes=[], cache_handler=MemoryCacheHandler())
        )
        self._open = False
        self._open_lock = asyncio.Lock()

    async def __aenter__(self) -> Self:
        await self.open()
        return self

    async def __aexit__(self, *_) -> None:
        await self.close()

    async def open(self) -> None:
        if self._open:
            return
        # Research tools run in parallel and may all open the client at once.
        async with self._open_lock:
            if self._open:
                return
            await self._client.http.open()
            self._open = True

    async def close(self) -> None:
        if not self._open:
            return
        self._open = False
        # A closed SpotifyClient cannot reopen, so injected clients stay with
        # their owner: the backend shares one across all agent runs.
        if self._owns_client:
            await self._client.aclose()

    @contextmanager
    def retrying(self, hook: OnRetryHook) -> Iterator[None]:
        """Report throttled requests of this task to ``hook`` while they retry."""
        with self._client.retry_hook(hook):
            yield

    async def search_tracks(self, query: str, *, limit: int = 10) -> TrackResults:
        await self.open()
        tracks = await _collect_search_results(
            self._client.tracks.iter_search, query, limit
        )
        logger.info("Spotify track search %r found %d", query, len(tracks))
        if not tracks:
            return TrackResults(content="No tracks found.", tracks=())
        return _track_results(tracks)

    async def search_playlists(self, query: str, *, limit: int = 10) -> PlaylistResults:
        await self.open()
        playlists = await _collect_search_results(
            self._client.playlists.iter_search, query, limit
        )
        logger.info("Spotify playlist search %r found %d", query, len(playlists))
        if not playlists:
            return PlaylistResults(content="No playlists found.", playlists=())
        return PlaylistResults(
            content="\n".join(_playlist_tag(playlist) for playlist in playlists),
            playlists=tuple(_found_playlist(playlist) for playlist in playlists),
        )

    async def get_playlist_tracks(
        self, playlist: str, *, offset: int = 0
    ) -> TrackResults:
        playlist_id = spotify_id(_normalize_spotify_id(playlist, "playlist"))
        offset = max(0, offset)
        await self.open()
        # playlists.items() needs a user token in Development Mode. Agent runs
        # only have an app token, which the legacy route still accepts for
        # public playlists.
        page = await self._client.http.get(
            f"/playlists/{playlist_id}/tracks",
            params={
                "limit": _PLAYLIST_PAGE_SIZE,
                "offset": offset,
                "additional_types": "track",
            },
            require_user=False,
            response_model=PagingPlaylistTrack,
        )
        tracks = _playlist_items(page.items)
        logger.info(
            "Spotify playlist %s page at %d has %d tracks",
            playlist_id,
            offset,
            len(tracks),
        )
        if not tracks:
            content = "Playlist is empty." if offset == 0 else "No more tracks."
            return TrackResults(content=content, tracks=())
        result = _track_results(tracks)
        footer = _playlist_page_footer(
            offset=offset,
            page_count=len(tracks),
            total=page.total,
            has_next=bool(page.next),
        )
        return TrackResults(content=f"{result.content}\n{footer}", tracks=result.tracks)


# Playlists are read one page at a time instead of expanding the whole playlist
# into a single tool result, which bloats the context for large playlists.
_PLAYLIST_PAGE_SIZE = 50
# Spotify's Development Mode rejects search pages larger than 10 items.
_SEARCH_PAGE_SIZE = 10


async def _collect_search_results[T](
    search: Callable[..., AsyncIterator[T | None]],
    query: str,
    limit: int,
) -> list[T]:
    results: list[T] = []
    pages = cast(
        AsyncGenerator[T | None],
        search(query, limit=min(limit, _SEARCH_PAGE_SIZE)),
    )
    async with aclosing(pages) as items:
        async for item in items:
            if item is None:
                continue
            results.append(item)
            if len(results) == limit:
                break
    return results


def _track_results(tracks: list[Track]) -> TrackResults:
    found = tuple(
        track
        for track in (_found_track(track) for track in tracks)
        if track is not None
    )
    content = "\n".join(
        tag(
            "track",
            [
                ("uri", track.uri),
                ("label", release_label(track.artist, track.title, track.year)),
            ],
        )
        for track in found
    )
    return TrackResults(content=content, tracks=found)


def _found_track(track: Track) -> FoundTrack | None:
    if not track.uri or not track.uri.startswith("spotify:track:"):
        return None
    album = track.album
    return FoundTrack(
        uri=track.uri,
        title=track.name or "Unknown title",
        artist=_artist_names(track.artists),
        year=_release_year(album.release_date if album else None),
        cover_url=_cover_url(album.images) if album else None,
    )


def _found_playlist(playlist: Playlist | SimplifiedPlaylist) -> FoundPlaylist:
    return FoundPlaylist(
        id=playlist.id or "",
        name=playlist.name or "Unknown playlist",
        cover_url=_cover_url(playlist.images),
    )


def _playlist_tag(playlist: Playlist | SimplifiedPlaylist) -> str:
    items = playlist.items
    track_count = items.total if items and items.total is not None else 0
    return tag(
        "playlist",
        [("id", playlist.id), ("label", playlist.name), ("tracks", str(track_count))],
    )


def _playlist_items(items: list | None) -> list[Track]:
    tracks: list[Track] = []
    for playlist_item in items or []:
        item = playlist_item.item
        if item is not None and getattr(item, "type", None) == "track":
            tracks.append(item)
    return tracks


def _playlist_page_footer(
    *,
    offset: int,
    page_count: int,
    total: int | None,
    has_next: bool,
) -> str:
    first = offset + 1
    last = offset + page_count
    scope = (
        f"Showing tracks {first}-{last} of {total}."
        if total is not None
        else f"Showing tracks {first}-{last}."
    )
    if not has_next:
        return f"{scope} End of playlist."
    return (
        f"{scope} More tracks available - call get_spotify_playlist_tracks "
        f"again with offset={last} to load the next page."
    )


def _cover_url(images: list[Image] | None) -> str | None:
    return images[0].url if images else None


def _artist_names(artists: list[SimplifiedArtist] | None) -> str:
    names = [artist.name for artist in (artists or []) if artist and artist.name]
    return ", ".join(names) if names else "Unknown artist"


def _release_year(release_date: str | None) -> int | None:
    if release_date and len(release_date) >= 4 and release_date[:4].isdigit():
        return int(release_date[:4])
    return None


def _normalize_spotify_id(value: str, resource_type: str) -> str:
    prefix = f"spotify:{resource_type}:"
    if value.startswith(prefix):
        return value[len(prefix) :]

    marker = f"/{resource_type}/"
    if marker in value:
        tail = value.split(marker, 1)[1]
        return tail.split("?", 1)[0].split("/", 1)[0]

    return value
