import asyncio
from collections.abc import Awaitable

from spotifyify import Image, Spotifyify, Track
from spotifyify.schemas import Artist, SimplifiedPlaylist

from backend.features.spotify.application.ports import (
    DEFAULT_SPOTIFY_SEARCH_TYPES,
    SpotifyArtist,
    SpotifyPlaylist,
    SpotifySearchType,
    SpotifyTrack,
    SpotifyUnifiedSearchResult,
)

type SearchTaskResult = list[SpotifyTrack] | list[SpotifyPlaylist] | list[SpotifyArtist]


class SpotifyService:
    def __init__(self, spotify: Spotifyify) -> None:
        self._spotify = spotify

    async def search_unified(
        self,
        *,
        query: str,
        limit: int = 20,
        types: set[SpotifySearchType] | None = None,
    ) -> SpotifyUnifiedSearchResult:
        normalized_query = query.strip()
        if not normalized_query:
            return SpotifyUnifiedSearchResult(tracks=[], playlists=[], artists=[])

        requested_types = types or set(DEFAULT_SPOTIFY_SEARCH_TYPES)
        search_tasks: dict[SpotifySearchType, Awaitable[SearchTaskResult]] = {}

        if SpotifySearchType.TRACK in requested_types:
            search_tasks[SpotifySearchType.TRACK] = self._search_tracks(
                query=normalized_query,
                limit=limit,
            )
        if SpotifySearchType.PLAYLIST in requested_types:
            search_tasks[SpotifySearchType.PLAYLIST] = self._search_playlists(
                query=normalized_query,
                limit=limit,
            )
        if SpotifySearchType.ARTIST in requested_types:
            search_tasks[SpotifySearchType.ARTIST] = self._search_artists(
                query=normalized_query,
                limit=limit,
            )

        if not search_tasks:
            return SpotifyUnifiedSearchResult(tracks=[], playlists=[], artists=[])

        task_results = await asyncio.gather(*search_tasks.values())
        results_by_type = dict(zip(search_tasks, task_results, strict=False))

        return SpotifyUnifiedSearchResult(
            tracks=list(results_by_type.get(SpotifySearchType.TRACK, [])),
            playlists=list(results_by_type.get(SpotifySearchType.PLAYLIST, [])),
            artists=list(results_by_type.get(SpotifySearchType.ARTIST, [])),
        )

    async def _search_tracks(
        self, *, query: str, limit: int = 20
    ) -> list[SpotifyTrack]:
        normalized_query = query.strip()
        if not normalized_query:
            return []

        result = await self._spotify.tracks.find(normalized_query, limit=limit)
        return [
            _to_spotify_track(track)
            for track in result.items or []
            if track.id and track.name
        ]

    async def _search_playlists(
        self, *, query: str, limit: int = 20
    ) -> list[SpotifyPlaylist]:
        normalized_query = query.strip()
        if not normalized_query:
            return []

        result = await self._spotify.playlists.find(normalized_query, limit=limit)
        return [
            _to_spotify_playlist(playlist)
            for playlist in result.items or []
            if playlist.id and playlist.name
        ]

    async def _search_artists(
        self, *, query: str, limit: int = 20
    ) -> list[SpotifyArtist]:
        normalized_query = query.strip()
        if not normalized_query:
            return []

        result = await self._spotify.artists.find(normalized_query, limit=limit)
        return [
            _to_spotify_artist(artist)
            for artist in result.items or []
            if artist.id and artist.name
        ]


def _to_spotify_playlist(playlist: SimplifiedPlaylist) -> SpotifyPlaylist:
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
    return SpotifyTrack(
        id=track.id or "",
        title=track.name or "",
        artist=artists,
        album=album.name if album else None,
        year=_release_year(album.release_date if album else None),
        cover_url=_cover_url(album.images if album else None),
        preview_url=track.preview_url,
    )


def _to_spotify_artist(artist: Artist) -> SpotifyArtist:
    followers = artist.followers.total if artist.followers else None
    image_url = _cover_url(artist.images)
    genres = [genre for genre in (artist.genres or []) if genre]
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
