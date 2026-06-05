import asyncio
import logging
from collections.abc import Iterator
from contextlib import contextmanager
from types import SimpleNamespace
from typing import Any, cast

from backend.features.spotify.application import (
    SpotifySearchType,
    SpotifyUnifiedSearchResult,
)
from backend.features.spotify.infrastructure.spotify_search_cache import (
    SpotifySearchCache,
)
from backend.features.spotify.infrastructure.spotify_playlist_creator import (
    SpotifyPlaylistCreator,
)
from backend.features.spotify.infrastructure.spotify_search import SpotifySearch


def _make_search(spotify: Any) -> SpotifySearch:
    return SpotifySearch(
        spotify=spotify,
        search_cache=SpotifySearchCache(),
    )


def _make_playlist_creator() -> SpotifyPlaylistCreator:
    return SpotifyPlaylistCreator()


class _TracksStub:
    def __init__(self, items: list[SimpleNamespace]) -> None:
        self._items = items
        self.received_query: str | None = None
        self.received_limit: int | None = None
        self.call_count = 0

    async def find(self, query: str, *, limit: int) -> SimpleNamespace:
        self.call_count += 1
        self.received_query = query
        self.received_limit = limit
        return SimpleNamespace(items=self._items)


class _ArtistsStub:
    def __init__(self, items: list[SimpleNamespace]) -> None:
        self._items = items
        self.received_query: str | None = None
        self.received_limit: int | None = None
        self.call_count = 0

    async def find(self, query: str, *, limit: int) -> SimpleNamespace:
        self.call_count += 1
        self.received_query = query
        self.received_limit = limit
        return SimpleNamespace(items=self._items)


class _PlaylistsStub:
    def __init__(self, items: list[SimpleNamespace]) -> None:
        self._items = items
        self.received_query: str | None = None
        self.received_limit: int | None = None
        self.call_count = 0

    async def find(self, query: str, *, limit: int) -> SimpleNamespace:
        self.call_count += 1
        self.received_query = query
        self.received_limit = limit
        return SimpleNamespace(items=self._items)


class _SpotifyStub:
    def __init__(
        self,
        *,
        track_items: list[SimpleNamespace] | None = None,
        playlist_items: list[SimpleNamespace] | None = None,
        artist_items: list[SimpleNamespace] | None = None,
    ) -> None:
        self.tracks = _TracksStub(items=track_items or [])
        self.playlists = _PlaylistsStub(items=playlist_items or [])
        self.artists = _ArtistsStub(items=artist_items or [])
        self.retry_hook_callback = None

    @contextmanager
    def retry_hook(self, hook) -> Iterator[None]:
        self.retry_hook_callback = hook
        yield
        self.retry_hook_callback = None


def _make_track() -> SimpleNamespace:
    return SimpleNamespace(
        id="1",
        name="Starlight",
        artists=[SimpleNamespace(name="Muse")],
        album=SimpleNamespace(
            name="Black Holes and Revelations",
            release_date="2006-01-01",
            images=[SimpleNamespace(url="https://example.com/cover.jpg")],
        ),
        external_urls=SimpleNamespace(
            spotify="https://open.spotify.com/track/1",
        ),
    )


def _make_artist() -> SimpleNamespace:
    return SimpleNamespace(
        id="artist-1",
        name="Muse",
        genres=["alternative rock", "rock"],
        followers=SimpleNamespace(total=1234567),
        popularity=91,
        images=[SimpleNamespace(url="https://example.com/muse.jpg")],
    )


def _make_playlist() -> SimpleNamespace:
    return SimpleNamespace(
        id="playlist-1",
        name="Muse Essentials",
        items=SimpleNamespace(total=42),
        images=[SimpleNamespace(url="https://example.com/playlist.jpg")],
        owner=SimpleNamespace(display_name="Spotify"),
    )


class TestSpotifySearch:
    def test_search_tracks_uses_default_limit(self) -> None:
        spotify = _SpotifyStub(track_items=[_make_track()])
        service = _make_search(cast(Any, spotify))

        result = asyncio.run(service._search_tracks(query="muse"))

        assert len(result) == 1
        assert result[0].title == "Starlight"
        assert result[0].artist == "Muse"
        assert spotify.tracks.received_query == "muse"
        assert spotify.tracks.received_limit == 20

    def test_search_tracks_uses_explicit_limit(self) -> None:
        spotify = _SpotifyStub(track_items=[_make_track()])
        service = _make_search(cast(Any, spotify))

        result = asyncio.run(service._search_tracks(query="muse", limit=7))

        assert len(result) == 1
        assert spotify.tracks.received_query == "muse"
        assert spotify.tracks.received_limit == 7

    def test_search_tracks_short_circuits_blank_query(self) -> None:
        spotify = _SpotifyStub(track_items=[_make_track()])
        service = _make_search(cast(Any, spotify))

        result = asyncio.run(service._search_tracks(query="   "))

        assert result == []
        assert spotify.tracks.received_query is None
        assert spotify.tracks.received_limit is None

    def test_search_artists_uses_default_limit(self) -> None:
        spotify = _SpotifyStub(artist_items=[_make_artist()])
        service = _make_search(cast(Any, spotify))

        result = asyncio.run(service._search_artists(query="muse"))

        assert len(result) == 1
        assert result[0].name == "Muse"
        assert result[0].genres == ["alternative rock", "rock"]
        assert result[0].followers == 1234567
        assert result[0].popularity == 91
        assert result[0].image_url == "https://example.com/muse.jpg"
        assert spotify.artists.received_query == "muse"
        assert spotify.artists.received_limit == 20

    def test_search_artists_short_circuits_blank_query(self) -> None:
        spotify = _SpotifyStub(artist_items=[_make_artist()])
        service = _make_search(cast(Any, spotify))

        result = asyncio.run(service._search_artists(query="   "))

        assert result == []
        assert spotify.artists.received_query is None
        assert spotify.artists.received_limit is None

    def test_search_unified_only_calls_requested_types(self) -> None:
        spotify = _SpotifyStub(
            track_items=[_make_track()],
            playlist_items=[_make_playlist()],
            artist_items=[_make_artist()],
        )
        service = _make_search(cast(Any, spotify))

        result = asyncio.run(
            service.search(
                query="muse",
                limit=5,
                types={SpotifySearchType.ARTIST},
            )
        )

        assert result.tracks == []
        assert result.playlists == []
        assert len(result.artists) == 1
        assert result.artists[0].name == "Muse"
        assert spotify.tracks.received_query is None
        assert spotify.playlists.received_query is None
        assert spotify.artists.received_query == "muse"
        assert spotify.artists.received_limit == 5

    def test_search_unified_returns_all_requested_types(self) -> None:
        spotify = _SpotifyStub(
            track_items=[_make_track()],
            playlist_items=[_make_playlist()],
            artist_items=[_make_artist()],
        )
        service = _make_search(cast(Any, spotify))

        result = asyncio.run(service.search(query="muse"))

        assert len(result.tracks) == 1
        assert len(result.playlists) == 1
        assert len(result.artists) == 1
        assert spotify.tracks.received_query == "muse"
        assert spotify.playlists.received_query == "muse"
        assert spotify.artists.received_query == "muse"

    def test_search_unified_short_circuits_blank_query(self) -> None:
        spotify = _SpotifyStub(
            track_items=[_make_track()],
            playlist_items=[_make_playlist()],
            artist_items=[_make_artist()],
        )
        service = _make_search(cast(Any, spotify))

        result = asyncio.run(service.search(query="  "))

        assert result.tracks == []
        assert result.playlists == []
        assert result.artists == []
        assert spotify.tracks.received_query is None
        assert spotify.playlists.received_query is None
        assert spotify.artists.received_query is None

    def test_search_unified_debounces_superseded_requests(self) -> None:
        spotify = _SpotifyStub(track_items=[_make_track()])
        service = _make_search(cast(Any, spotify))

        async def _run() -> tuple[Any, Any]:
            first = asyncio.create_task(
                service.search(
                    query="sk",
                    limit=8,
                    types={SpotifySearchType.TRACK},
                    requester_id="user-1",
                )
            )
            await asyncio.sleep(0.01)
            second = asyncio.create_task(
                service.search(
                    query="ski",
                    limit=8,
                    types={SpotifySearchType.TRACK},
                    requester_id="user-1",
                )
            )
            return await asyncio.gather(first, second)

        first_result, second_result = asyncio.run(_run())

        assert first_result.tracks == []
        assert first_result.playlists == []
        assert first_result.artists == []
        assert len(second_result.tracks) == 1
        assert spotify.tracks.call_count == 1
        assert spotify.tracks.received_query == "ski"

    def test_search_unified_coalesces_identical_inflight_requests(self) -> None:
        spotify = _SpotifyStub(track_items=[_make_track()])
        service = _make_search(cast(Any, spotify))

        async def _run() -> tuple[Any, Any]:
            first = asyncio.create_task(
                service.search(
                    query="muse",
                    limit=8,
                    types={SpotifySearchType.TRACK},
                    requester_id="user-1",
                )
            )
            second = asyncio.create_task(
                service.search(
                    query="muse",
                    limit=8,
                    types={SpotifySearchType.TRACK},
                    requester_id="user-1",
                )
            )
            return await asyncio.gather(first, second)

        first_result, second_result = asyncio.run(_run())

        assert len(first_result.tracks) == 1
        assert len(second_result.tracks) == 1
        assert spotify.tracks.call_count == 1

    def test_execute_unified_search_logs_spotifyify_retry_hook(self, caplog) -> None:
        spotify = _SpotifyStub()
        service = _make_search(cast(Any, spotify))

        async def _execute_unified_search(
            *,
            query: str,
            limit: int,
            types: set[SpotifySearchType],
        ) -> SpotifyUnifiedSearchResult:
            assert spotify.retry_hook_callback is not None
            spotify.retry_hook_callback(
                SimpleNamespace(
                    method=SimpleNamespace(value="GET"),
                    path="/search",
                    status_code=429,
                    retry_in_seconds=2.0,
                    retry_number=1,
                    max_retries=3,
                )
            )
            return SpotifyUnifiedSearchResult(tracks=[], playlists=[], artists=[])

        service._execute_unified_search = _execute_unified_search  # type: ignore[method-assign]

        with caplog.at_level(
            logging.WARNING,
            logger="backend.features.spotify.infrastructure.spotify_search",
        ):
            result = asyncio.run(
                service._execute_unified_search_with_retry_logging(
                    query="muse",
                    limit=20,
                    types={SpotifySearchType.TRACK},
                )
            )

        assert result == SpotifyUnifiedSearchResult(tracks=[], playlists=[], artists=[])
        assert spotify.retry_hook_callback is None
        assert "Retrying Spotifyify request" in caplog.text
        assert "path=/search" in caplog.text
        assert "status_code=429" in caplog.text


class TestSpotifyPlaylistCreator:
    def test_create_private_playlist_uses_user_token_flow(self) -> None:
        service = _make_playlist_creator()
        calls: list[tuple[str, str, dict | None, str]] = []
        responses: list[dict | None] = [{"id": "user-1"}, {"id": "playlist-1"}]

        async def _request_user_api(
            *,
            access_token: str,
            method: str,
            path: str,
            payload: dict | None = None,
        ) -> dict | list | None:
            calls.append((method, path, payload, access_token))
            return responses.pop(0)

        service._request_user_api = _request_user_api  # type: ignore[method-assign]

        try:
            playlist_id = asyncio.run(
                service.create_private_playlist(
                    access_token="token-123",
                    name="Roadtrip",
                    description="Late night drive",
                )
            )
        finally:
            asyncio.run(service.aclose())

        assert playlist_id == "playlist-1"
        assert calls == [
            ("GET", "/me", None, "token-123"),
            (
                "POST",
                "/users/user-1/playlists",
                {
                    "name": "Roadtrip",
                    "description": "Late night drive",
                    "public": False,
                },
                "token-123",
            ),
        ]

    def test_update_playlist_and_replace_tracks_use_user_token(self) -> None:
        service = _make_playlist_creator()
        calls: list[tuple[str, str, dict | None, str]] = []

        async def _request_user_api(
            *,
            access_token: str,
            method: str,
            path: str,
            payload: dict | None = None,
        ) -> dict | list | None:
            calls.append((method, path, payload, access_token))
            return None

        service._request_user_api = _request_user_api  # type: ignore[method-assign]

        try:
            asyncio.run(
                service.update_playlist_details(
                    access_token="token-123",
                    playlist_id="playlist-1",
                    name="Updated",
                    description="Updated description",
                )
            )
            asyncio.run(
                service.replace_playlist_tracks(
                    access_token="token-123",
                    playlist_id="playlist-1",
                    track_uris=["spotify:track:1", "spotify:track:2"],
                )
            )
        finally:
            asyncio.run(service.aclose())

        assert calls == [
            (
                "PUT",
                "/playlists/playlist-1",
                {"name": "Updated", "description": "Updated description"},
                "token-123",
            ),
            (
                "PUT",
                "/playlists/playlist-1/tracks",
                {"uris": ["spotify:track:1", "spotify:track:2"]},
                "token-123",
            ),
        ]
