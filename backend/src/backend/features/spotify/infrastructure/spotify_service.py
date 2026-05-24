import asyncio
from collections.abc import Awaitable

import httpx
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
    _SPOTIFY_API_BASE_URL = "https://api.spotify.com/v1"

    def __init__(self, spotify: Spotifyify) -> None:
        self._spotify = spotify

    async def create_private_playlist(
        self,
        *,
        access_token: str,
        name: str,
        description: str,
    ) -> str:
        user_id = await self._get_current_user_id(access_token=access_token)
        payload = {
            "name": name,
            "description": description,
            "public": False,
        }
        data = await self._request_user_api(
            access_token=access_token,
            method="POST",
            path=f"/users/{user_id}/playlists",
            payload=payload,
        )
        if not isinstance(data, dict):
            raise ValueError("Spotify playlist creation failed")

        playlist_id = data.get("id")
        if not isinstance(playlist_id, str) or not playlist_id.strip():
            raise ValueError("Spotify playlist creation did not return an id")
        return playlist_id

    async def update_playlist_details(
        self,
        *,
        access_token: str,
        playlist_id: str,
        name: str,
        description: str,
    ) -> None:
        await self._request_user_api(
            access_token=access_token,
            method="PUT",
            path=f"/playlists/{playlist_id}",
            payload={"name": name, "description": description},
        )

    async def replace_playlist_tracks(
        self,
        *,
        access_token: str,
        playlist_id: str,
        track_uris: list[str],
    ) -> None:
        await self._request_user_api(
            access_token=access_token,
            method="PUT",
            path=f"/playlists/{playlist_id}/tracks",
            payload={"uris": track_uris},
        )

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
            if track is not None and track.id and track.name
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
            if playlist is not None and playlist.id and playlist.name
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
            if artist is not None and artist.id and artist.name
        ]

    async def _get_current_user_id(self, *, access_token: str) -> str:
        data = await self._request_user_api(
            access_token=access_token,
            method="GET",
            path="/me",
        )
        if not isinstance(data, dict):
            raise ValueError("Spotify user lookup failed")

        user_id = data.get("id")
        if not isinstance(user_id, str) or not user_id.strip():
            raise ValueError("Spotify user lookup did not return an id")
        return user_id

    async def _request_user_api(
        self,
        *,
        access_token: str,
        method: str,
        path: str,
        payload: dict | None = None,
    ) -> dict | list | None:
        headers = {"Authorization": f"Bearer {access_token}"}
        async with httpx.AsyncClient(
            base_url=self._SPOTIFY_API_BASE_URL,
            timeout=10.0,
        ) as client:
            response = await client.request(
                method=method,
                url=path,
                headers=headers,
                json=payload,
            )

        if response.status_code >= 400:
            try:
                response_payload = response.json()
            except ValueError:
                response_payload = None

            detail = response.text
            if isinstance(response_payload, dict):
                error = response_payload.get("error")
                if isinstance(error, dict):
                    detail = str(error.get("message") or detail)
                elif isinstance(error, str) and error.strip():
                    detail = error
            raise ValueError(
                f"Spotify API request failed ({response.status_code}): {detail}"
            )

        if response.status_code == 204 or not response.content:
            return None

        try:
            return response.json()
        except ValueError as exc:
            raise ValueError("Spotify API response was not valid JSON") from exc


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
