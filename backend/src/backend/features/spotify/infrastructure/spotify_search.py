import asyncio
import logging
from collections.abc import AsyncGenerator, AsyncIterator, Awaitable, Callable
from contextlib import aclosing
from typing import cast

from spotifyify import (
    Artist,
    Image,
    RetryEvent,
    SimplifiedPlaylist,
    SpotifyAPIError,
    SpotifyClient,
    Track,
)

from backend.features.spotify.application import SpotifySearchGateway
from backend.features.spotify.domain import (
    DEFAULT_SPOTIFY_SEARCH_TYPES,
    SpotifyArtist,
    SpotifyPlaylist,
    SpotifySearchType,
    SpotifyTrack,
    SpotifyUnifiedSearchResult,
)
from backend.features.spotify.infrastructure.spotify_search_cache import (
    SpotifySearchCache,
)

logger = logging.getLogger(__name__)

type SearchTaskResult = list[SpotifyTrack] | list[SpotifyPlaylist] | list[SpotifyArtist]

# Spotify's Development Mode rejects search pages larger than 10 items.
_SEARCH_PAGE_SIZE = 10


class SpotifyifySearch(SpotifySearchGateway):
    def __init__(
        self,
        spotify: SpotifyClient,
        search_cache: SpotifySearchCache,
    ) -> None:
        self._spotify = spotify
        self._search_cache = search_cache

    async def search(
        self,
        *,
        query: str,
        limit: int = 20,
        types: set[SpotifySearchType] | None = None,
        requester_id: str | None = None,
    ) -> SpotifyUnifiedSearchResult:
        normalized_query = query.strip()
        if not normalized_query:
            return SpotifyUnifiedSearchResult(
                tracks=(),
                playlists=(),
                artists=(),
            )

        requested_types = (
            types if types is not None else set(DEFAULT_SPOTIFY_SEARCH_TYPES)
        )

        if not requested_types:
            return SpotifyUnifiedSearchResult(
                tracks=(),
                playlists=(),
                artists=(),
            )

        cache_key = self._build_search_cache_key(
            query=normalized_query,
            limit=limit,
            types=requested_types,
        )
        debounce_scope = self._build_debounce_scope(
            requester_id=requester_id,
            limit=limit,
            types=requested_types,
        )

        if await self._search_cache.is_superseded_search(
            debounce_scope=debounce_scope,
            cache_key=cache_key,
        ):
            cached_result = await self._search_cache.get_cached_result(
                cache_key=cache_key,
            )
            if cached_result is not None:
                return cached_result
            return SpotifyUnifiedSearchResult(
                tracks=(),
                playlists=(),
                artists=(),
            )

        return await self._search_cache.run_with_cache(
            cache_key=cache_key,
            producer=lambda: self._execute_unified_search_with_retry_logging(
                query=normalized_query,
                limit=limit,
                types=requested_types,
            ),
        )

    async def get_track_by_id(self, *, track_id: str) -> SpotifyTrack | None:
        normalized_track_id = track_id.strip()
        if not normalized_track_id:
            return None

        try:
            with self._spotify.retry_hook(_log_spotifyify_retry):
                track = await self._spotify.tracks.get(normalized_track_id)
        except ValueError:
            # spotifyify rejects malformed IDs before sending a request.
            return None
        except SpotifyAPIError as error:
            if error.status_code == 404:
                return None
            raise

        if not track.id or not track.name:
            return None
        return _to_spotify_track(track)

    async def _execute_unified_search_with_retry_logging(
        self,
        *,
        query: str,
        limit: int,
        types: set[SpotifySearchType],
    ) -> SpotifyUnifiedSearchResult:
        with self._spotify.retry_hook(_log_spotifyify_retry):
            return await self._execute_unified_search(
                query=query,
                limit=limit,
                types=types,
            )

    async def _execute_unified_search(
        self,
        *,
        query: str,
        limit: int,
        types: set[SpotifySearchType],
    ) -> SpotifyUnifiedSearchResult:
        search_tasks: dict[
            SpotifySearchType,
            Awaitable[SearchTaskResult],
        ] = {}

        if SpotifySearchType.TRACK in types:
            search_tasks[SpotifySearchType.TRACK] = self._search_tracks(
                query=query,
                limit=limit,
            )
        if SpotifySearchType.PLAYLIST in types:
            search_tasks[SpotifySearchType.PLAYLIST] = self._search_playlists(
                query=query,
                limit=limit,
            )
        if SpotifySearchType.ARTIST in types:
            search_tasks[SpotifySearchType.ARTIST] = self._search_artists(
                query=query,
                limit=limit,
            )

        if not search_tasks:
            return SpotifyUnifiedSearchResult(
                tracks=(),
                playlists=(),
                artists=(),
            )

        task_results = await asyncio.gather(*search_tasks.values())
        results_by_type = dict(zip(search_tasks, task_results, strict=False))

        return SpotifyUnifiedSearchResult(
            tracks=tuple(results_by_type.get(SpotifySearchType.TRACK, ())),
            playlists=tuple(results_by_type.get(SpotifySearchType.PLAYLIST, ())),
            artists=tuple(results_by_type.get(SpotifySearchType.ARTIST, ())),
        )

    def _build_debounce_scope(
        self,
        *,
        requester_id: str | None,
        limit: int,
        types: set[SpotifySearchType],
    ) -> str:
        requester_scope = requester_id or "anonymous"
        type_scope = ",".join(sorted(search_type.value for search_type in types))
        return f"{requester_scope}|{limit}|{type_scope}"

    def _build_search_cache_key(
        self,
        *,
        query: str,
        limit: int,
        types: set[SpotifySearchType],
    ) -> str:
        normalized_query = " ".join(query.casefold().split())
        type_scope = ",".join(sorted(search_type.value for search_type in types))
        return f"{normalized_query}|{limit}|{type_scope}"

    async def _search_tracks(
        self, *, query: str, limit: int = 20
    ) -> list[SpotifyTrack]:
        normalized_query = query.strip()
        if not normalized_query:
            return []

        tracks = await _collect_search_results(
            self._spotify.tracks.iter_search,
            normalized_query,
            limit,
        )
        return [_to_spotify_track(track) for track in tracks if _has_id_and_name(track)]

    async def _search_playlists(
        self, *, query: str, limit: int = 20
    ) -> list[SpotifyPlaylist]:
        normalized_query = query.strip()
        if not normalized_query:
            return []

        playlists = await _collect_search_results(
            self._spotify.playlists.iter_search,
            normalized_query,
            limit,
        )
        return [
            _to_spotify_playlist(playlist)
            for playlist in playlists
            if _has_id_and_name(playlist)
        ]

    async def _search_artists(
        self, *, query: str, limit: int = 20
    ) -> list[SpotifyArtist]:
        normalized_query = query.strip()
        if not normalized_query:
            return []

        artists = await _collect_search_results(
            self._spotify.artists.iter_search,
            normalized_query,
            limit,
        )
        return [
            _to_spotify_artist(artist) for artist in artists if _has_id_and_name(artist)
        ]


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


def _log_spotifyify_retry(event: RetryEvent) -> None:
    logger.warning(
        "Retrying Spotifyify request: method=%s path=%s status_code=%d "
        "retry_in_seconds=%s retry=%d/%d",
        event.method.value,
        event.path,
        event.status_code,
        event.retry_in_seconds,
        event.retry_number,
        event.max_retries,
    )


def _to_spotify_playlist(
    playlist: SimplifiedPlaylist,
) -> SpotifyPlaylist:
    total = playlist.items.total if playlist.items else None
    cover_url = playlist.images[0].url if playlist.images else None
    owner = playlist.owner.display_name if playlist.owner else None
    return SpotifyPlaylist(
        id=playlist.id or "",
        name=playlist.name or "",
        owner=owner,
        cover_url=cover_url,
        total_tracks=total,
    )


def _to_spotify_track(track: Track) -> SpotifyTrack:
    album = track.album
    artists = ", ".join(artist.name for artist in track.artists or [] if artist.name)
    external_urls = track.external_urls
    return SpotifyTrack(
        id=track.id or "",
        title=track.name or "",
        artist=artists,
        album=album.name if album else None,
        year=_release_year(album.release_date if album else None),
        cover_url=_cover_url(album.images if album else None),
        url=external_urls.spotify if external_urls else None,
    )


def _to_spotify_artist(artist: Artist) -> SpotifyArtist:
    followers = artist.followers.total if artist.followers else None
    image_url = _cover_url(artist.images)
    genres = tuple(genre for genre in (artist.genres or ()) if genre)
    return SpotifyArtist(
        id=artist.id or "",
        name=artist.name or "",
        genres=genres,
        followers=followers,
        popularity=artist.popularity,
        image_url=image_url,
    )


def _release_year(release_date: str | None) -> int | None:
    if not release_date:
        return None

    year = release_date.split("-", maxsplit=1)[0]
    try:
        return int(year)
    except ValueError:
        return None


def _cover_url(images: list[Image] | None) -> str | None:
    if not images:
        return None
    return images[0].url


def _has_id_and_name(item: Track | SimplifiedPlaylist | Artist) -> bool:
    return bool(item.id and item.name)
