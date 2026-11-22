import logging
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Self

from pydantic import BaseModel
from spotifyify import (
    RetryEvent,
    Spotifyify,
    Track,
)

from agent.tools.handler.spotify_rendering import (
    SpotifyPlaylistPreview,
    SpotifyTrackLookupResult,
    cover_url,
    format_album,
    format_playlist,
    playlist_preview,
    track_cover_url,
    track_lookup_result,
    track_release_date,
)
from agent.tools.params import (
    AlbumTracksParams,
    ArtistAlbumsParams,
    ArtistTopTracksParams,
    PlaylistIdParams,
    SearchParams,
)
from agent.tools.retry_reporting import report_retry

logger = logging.getLogger(__name__)

# Playlists are discovered progressively one page at a time instead of expanding
# the whole playlist into a single tool result, which used to bloat the LLM
# context by tens of thousands of tokens for large playlists.
_PLAYLIST_PAGE_SIZE = 50


class SpotifyPlaylistLookupResult(BaseModel):
    content: str
    playlists: list[SpotifyPlaylistPreview]


class Spotify:
    def __init__(self, client: Spotifyify | None = None) -> None:
        self._client = client if client is not None else Spotifyify(scopes=[])
        self._open = False

    async def __aenter__(self) -> Self:
        await self.open()
        return self

    async def __aexit__(self, *_) -> None:
        await self.close()

    async def open(self) -> None:
        if self._open:
            return
        await self._client.http.open()
        self._open = True

    async def close(self) -> None:
        if not self._open:
            return
        await self._client.close()
        self._open = False

    async def search_tracks(self, params: SearchParams) -> SpotifyTrackLookupResult:
        await self.open()
        query_limit = min(params.limit, 50)
        logger.info(
            "Spotify search_tracks: query=%r limit=%d",
            params.query,
            query_limit,
        )
        with self._retry_logging():
            page = await self._client.tracks.find(
                params.query,
                limit=query_limit,
            )
        tracks = page.items or []
        logger.info(
            "Spotify search_tracks: found=%d query=%r",
            len(tracks),
            params.query,
        )
        if not tracks:
            return SpotifyTrackLookupResult(content="No tracks found.", tracks=[])
        return track_lookup_result(
            tracks,
            release_date_for=track_release_date,
            cover_url_for=track_cover_url,
        )

    async def search_albums(self, params: SearchParams) -> str:
        await self.open()
        query_limit = min(params.limit, 50)
        logger.info(
            "Spotify search_albums: query=%r limit=%d",
            params.query,
            query_limit,
        )
        with self._retry_logging():
            page = await self._client.albums.find(
                params.query,
                limit=query_limit,
            )
        albums = page.items or []
        logger.info(
            "Spotify search_albums: found=%d query=%r",
            len(albums),
            params.query,
        )
        if not albums:
            return "No albums found."
        return "\n".join(format_album(album) for album in albums)

    async def search_playlists(
        self, params: SearchParams
    ) -> SpotifyPlaylistLookupResult:
        await self.open()
        query_limit = min(params.limit, 50)
        logger.info(
            "Spotify search_playlists: query=%r limit=%d",
            params.query,
            query_limit,
        )
        with self._retry_logging():
            page = await self._client.playlists.find(
                params.query,
                limit=query_limit,
            )
        playlists = [playlist for playlist in (page.items or []) if playlist]
        logger.info(
            "Spotify search_playlists: found=%d query=%r",
            len(playlists),
            params.query,
        )
        if not playlists:
            return SpotifyPlaylistLookupResult(
                content="No playlists found.", playlists=[]
            )
        return SpotifyPlaylistLookupResult(
            content="\n".join(format_playlist(playlist) for playlist in playlists),
            playlists=[playlist_preview(playlist) for playlist in playlists],
        )

    async def get_artist_albums(self, params: ArtistAlbumsParams) -> str:
        artist_id = _normalize_spotify_id(params.artist_id, "artist")
        await self.open()
        logger.info(
            "Spotify get_artist_albums: artist_id=%s include_groups=%s limit=%d",
            artist_id,
            params.include_groups,
            params.limit,
        )
        with self._retry_logging():
            page = await self._client.artists.albums(
                artist_id,
                include_groups=params.include_groups,
                limit=params.limit,
            )
        albums = page.items or []
        logger.info(
            "Spotify get_artist_albums: found=%d artist_id=%s",
            len(albums),
            artist_id,
        )
        if not albums:
            return "No albums found."
        return "\n".join(format_album(album) for album in albums)

    async def get_artist_top_tracks(
        self,
        params: ArtistTopTracksParams,
    ) -> SpotifyTrackLookupResult:
        artist_id = _normalize_spotify_id(params.artist_id, "artist")
        await self.open()
        logger.info(
            "Spotify get_artist_top_tracks: artist_id=%s market=%s",
            artist_id,
            params.country,
        )
        with self._retry_logging():
            tracks = await self._client.artists.top_tracks(
                artist_id,
                market=params.country,
            )
        logger.info(
            "Spotify get_artist_top_tracks: found=%d artist_id=%s",
            len(tracks),
            artist_id,
        )
        if not tracks:
            return SpotifyTrackLookupResult(content="No top tracks found.", tracks=[])
        return track_lookup_result(
            tracks,
            release_date_for=track_release_date,
            cover_url_for=track_cover_url,
        )

    async def get_album_tracks(
        self,
        params: AlbumTracksParams,
    ) -> SpotifyTrackLookupResult:
        album_id = _normalize_spotify_id(params.album_id, "album")
        await self.open()
        logger.info("Spotify get_album_tracks: album_id=%s", album_id)
        with self._retry_logging():
            album = await self._client.albums.get(album_id)
            page = await self._client.albums.tracks(album_id, limit=50, offset=0)
        tracks = page.items or []
        logger.info(
            "Spotify get_album_tracks: found=%d album_id=%s",
            len(tracks),
            album_id,
        )
        if not tracks:
            return SpotifyTrackLookupResult(content="No tracks found.", tracks=[])
        album_cover_url = cover_url(album.images)
        return track_lookup_result(
            tracks,
            release_date_for=lambda _: album.release_date,
            cover_url_for=lambda _: album_cover_url,
        )

    async def get_playlist_tracks(
        self,
        params: PlaylistIdParams,
    ) -> SpotifyTrackLookupResult:
        playlist_id = _normalize_spotify_id(params.playlist_id, "playlist")
        offset = max(0, params.offset)
        await self.open()
        logger.info(
            "Spotify get_playlist_tracks: playlist_id=%s offset=%d",
            playlist_id,
            offset,
        )
        with self._retry_logging():
            page = await self._client.playlists.tracks(
                playlist_id,
                limit=_PLAYLIST_PAGE_SIZE,
                offset=offset,
                additional_types=["track"],
            )
        tracks = _extract_playlist_tracks(page.items)
        total = page.total
        logger.info(
            "Spotify get_playlist_tracks: found=%d offset=%d total=%s playlist_id=%s",
            len(tracks),
            offset,
            total,
            playlist_id,
        )
        if not tracks:
            content = "Playlist is empty." if offset == 0 else "No more tracks."
            return SpotifyTrackLookupResult(content=content, tracks=[])
        result = track_lookup_result(
            tracks,
            release_date_for=track_release_date,
            cover_url_for=track_cover_url,
        )
        footer = _playlist_page_footer(
            offset=offset,
            page_count=len(tracks),
            total=total,
            has_next=bool(page.next),
        )
        content = f"{result.content}\n{footer}" if footer else result.content
        return SpotifyTrackLookupResult(content=content, tracks=result.tracks)

    @contextmanager
    def _retry_logging(self) -> Iterator[None]:
        with self._client.retry_hook(_log_retry):
            yield


def _log_retry(event: RetryEvent) -> None:
    logger.warning(
        "Retrying Spotify request: method=%s path=%s status_code=%d "
        "retry_in_seconds=%s retry=%d/%d",
        event.method.value,
        event.path,
        event.status_code,
        event.retry_in_seconds,
        event.retry_number,
        event.max_retries,
    )
    report_retry(event)


def _extract_playlist_tracks(items: list | None) -> list[Track]:
    tracks: list[Track] = []
    for playlist_item in items or []:
        item = playlist_item.item or playlist_item.track
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
    if total is not None:
        scope = f"Showing tracks {first}-{last} of {total}."
    else:
        scope = f"Showing tracks {first}-{last}."
    if has_next:
        next_offset = offset + page_count
        return (
            f"{scope} More tracks available - call get_spotify_playlist_tracks "
            f"again with offset={next_offset} to load the next page."
        )
    return f"{scope} End of playlist."


def _normalize_spotify_id(value: str, resource_type: str) -> str:
    prefix = f"spotify:{resource_type}:"
    if value.startswith(prefix):
        return value[len(prefix) :]

    marker = f"/{resource_type}/"
    if marker in value:
        tail = value.split(marker, 1)[1]
        return tail.split("?", 1)[0].split("/", 1)[0]

    return value
