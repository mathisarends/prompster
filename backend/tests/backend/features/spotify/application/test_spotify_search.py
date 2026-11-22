import asyncio
import logging
from collections.abc import AsyncIterator, Callable, Iterator
from contextlib import asynccontextmanager, contextmanager
from types import SimpleNamespace
from typing import Any, cast

import httpx2
import pytest
from spotifyify import SpotifyClient

from backend.features.spotify.application import SpotifySearch, SpotifySearchGateway
from backend.features.spotify.domain import (
    InvalidSpotifyTrackUriError,
    SpotifySearchType,
    SpotifyTrack,
    SpotifyTrackNotFoundError,
    SpotifyTrackYearMissingError,
    SpotifyUnifiedSearchResult,
)
from backend.features.spotify.infrastructure.spotify_playlist_creator import (
    SpotifyPlaylistCreator,
)
from backend.features.spotify.infrastructure.spotify_search import SpotifyifySearch
from backend.features.spotify.infrastructure.spotify_search_cache import (
    SpotifySearchCache,
)


def _make_search(spotify: Any) -> SpotifyifySearch:
    return SpotifyifySearch(
        spotify=spotify,
        search_cache=SpotifySearchCache(),
    )


class _SpotifyTrackLookupStub(SpotifySearchGateway):
    def __init__(self, track: SpotifyTrack | None) -> None:
        self.track = track
        self.received_track_id: str | None = None

    async def search(
        self,
        *,
        query: str,
        limit: int = 20,
        types: set[SpotifySearchType] | None = None,
        requester_id: str | None = None,
    ) -> SpotifyUnifiedSearchResult:
        raise NotImplementedError

    async def get_track_by_id(self, *, track_id: str) -> SpotifyTrack | None:
        self.received_track_id = track_id
        return self.track


def _make_playlist_creator(spotify: Any | None = None) -> SpotifyPlaylistCreator:
    return SpotifyPlaylistCreator(spotify=spotify or _PlaylistCreatorSpotifyStub())


class _SearchStub:
    def __init__(self, items: list[SimpleNamespace]) -> None:
        self._items = items
        self.received_query: str | None = None
        self.received_limit: int | None = None
        self.call_count = 0

    async def iter_search(
        self, query: str, *, limit: int
    ) -> AsyncIterator[SimpleNamespace]:
        self.call_count += 1
        self.received_query = query
        self.received_limit = limit
        for item in self._items:
            yield item


class _SpotifyStub:
    def __init__(
        self,
        *,
        track_items: list[SimpleNamespace] | None = None,
        playlist_items: list[SimpleNamespace] | None = None,
        artist_items: list[SimpleNamespace] | None = None,
    ) -> None:
        self.tracks = _SearchStub(items=track_items or [])
        self.playlists = _SearchStub(items=playlist_items or [])
        self.artists = _SearchStub(items=artist_items or [])
        self.retry_hook_callback = None

    @contextmanager
    def retry_hook(self, hook) -> Iterator[None]:
        self.retry_hook_callback = hook
        yield
        self.retry_hook_callback = None


class _PlaylistCreatorPlaylistsStub:
    def __init__(self, spotify: _PlaylistCreatorSpotifyStub) -> None:
        self._spotify = spotify
        self.created_playlist_id = "playlist-1"
        self.calls: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = []

    async def create(
        self,
        name: str,
        *,
        public: bool = False,
        collaborative: bool = False,
        description: str = "",
        user_id: str | None = None,
    ) -> SimpleNamespace:
        self.calls.append(
            (
                "create",
                (name,),
                {
                    "public": public,
                    "collaborative": collaborative,
                    "description": description,
                    "user_id": user_id,
                },
            )
        )
        self._emit_retry()
        return SimpleNamespace(id=self.created_playlist_id)

    async def update(
        self,
        playlist_id: str,
        *,
        name: str | None = None,
        public: bool | None = None,
        collaborative: bool | None = None,
        description: str | None = None,
    ) -> None:
        self.calls.append(
            (
                "update",
                (playlist_id,),
                {
                    "name": name,
                    "public": public,
                    "collaborative": collaborative,
                    "description": description,
                },
            )
        )
        self._emit_retry()

    async def replace(self, playlist_id: str, uris: list[str]) -> str | None:
        self.calls.append(("replace", (playlist_id, list(uris)), {}))
        self._emit_retry()
        return "snapshot-1"

    def _emit_retry(self) -> None:
        if self._spotify.retry_hook_callback is None:
            return
        self._spotify.retry_hook_callback(
            SimpleNamespace(
                method=SimpleNamespace(value="PUT"),
                path="/playlists/playlist-1",
                status_code=429,
                retry_in_seconds=2.0,
                retry_number=1,
                max_retries=3,
            )
        )


class _PlaylistCreatorSpotifyStub:
    def __init__(self) -> None:
        self.playlists = _PlaylistCreatorPlaylistsStub(self)
        self.session_calls: list[tuple[str | None, Any]] = []
        self.retry_hook_callback = None

    @asynccontextmanager
    async def request_context(
        self,
        *,
        access_token: str | None = None,
        on_retry=None,
    ):
        self.session_calls.append((access_token, on_retry))
        self.retry_hook_callback = on_retry
        try:
            yield
        finally:
            self.retry_hook_callback = None


class _AppTokenProvider:
    async def get_access_token(
        self,
        require_user: bool,
        scope: str | list[str] | tuple[str, ...] | None = None,
    ) -> str:
        return "app-token"


def _track_payload(index: int) -> dict[str, Any]:
    return {
        "id": f"track{index}",
        "name": f"Track {index}",
        "type": "track",
        "uri": f"spotify:track:track{index}",
        "artists": [{"name": "Muse"}],
        "album": {
            "album_type": "album",
            "total_tracks": 1,
            "external_urls": {},
            "href": "https://api.spotify.com/v1/albums/album1",
            "id": "album1",
            "images": [],
            "name": "Origin",
            "release_date": "2001-06-18",
            "release_date_precision": "day",
            "type": "album",
            "uri": "spotify:album:album1",
            "artists": [],
        },
    }


def _paged_track_search(
    total: int,
    requested_limits: list[int],
) -> Callable[[httpx2.Request], httpx2.Response]:
    def handle(request: httpx2.Request) -> httpx2.Response:
        limit = int(request.url.params["limit"])
        offset = int(request.url.params["offset"])
        requested_limits.append(limit)
        end = offset + limit
        next_url = (
            f"https://api.spotify.com/v1/search?offset={end}&limit={limit}"
            if end < total
            else None
        )
        return httpx2.Response(
            200,
            json={
                "tracks": {
                    "href": "https://api.spotify.com/v1/search",
                    "limit": limit,
                    "offset": offset,
                    "total": total,
                    "next": next_url,
                    "previous": None,
                    "items": [
                        _track_payload(index)
                        for index in range(offset, min(end, total))
                    ],
                }
            },
        )

    return handle


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


class TestSpotifyTrackLookup:
    @pytest.mark.parametrize(
        "spotify_uri",
        [
            "spotify:track:track-id",
            "https://open.spotify.com/track/track-id?si=abc",
            "track-id",
        ],
    )
    def test_get_track_resolves_uri_and_returns_complete_track(
        self,
        spotify_uri: str,
    ) -> None:
        track = SpotifyTrack(
            id="track-id",
            title="Starlight",
            artist="Muse",
            year=2006,
        )
        gateway = _SpotifyTrackLookupStub(track)
        search = SpotifySearch(gateway=gateway)

        result = asyncio.run(search.get_track(spotify_uri=spotify_uri))

        assert result == track
        assert gateway.received_track_id == "track-id"

    @pytest.mark.parametrize("spotify_uri", ["", "spotify:album:album-id"])
    def test_get_track_rejects_invalid_uri(self, spotify_uri: str) -> None:
        gateway = _SpotifyTrackLookupStub(None)
        search = SpotifySearch(gateway=gateway)

        with pytest.raises(InvalidSpotifyTrackUriError):
            asyncio.run(search.get_track(spotify_uri=spotify_uri))

        assert gateway.received_track_id is None

    def test_get_track_raises_when_track_does_not_exist(self) -> None:
        gateway = _SpotifyTrackLookupStub(None)
        search = SpotifySearch(gateway=gateway)

        with pytest.raises(SpotifyTrackNotFoundError):
            asyncio.run(search.get_track(spotify_uri="spotify:track:missing"))

        assert gateway.received_track_id == "missing"

    def test_get_track_raises_when_release_year_is_missing(self) -> None:
        gateway = _SpotifyTrackLookupStub(
            SpotifyTrack(
                id="track-id",
                title="Starlight",
                artist="Muse",
                year=None,
            )
        )
        search = SpotifySearch(gateway=gateway)

        with pytest.raises(SpotifyTrackYearMissingError):
            asyncio.run(search.get_track(spotify_uri="spotify:track:track-id"))


class TestSpotifySearch:
    def test_search_tracks_uses_default_limit(self) -> None:
        spotify = _SpotifyStub(track_items=[_make_track()])
        service = _make_search(cast(Any, spotify))

        result = asyncio.run(service._search_tracks(query="muse"))

        assert len(result) == 1
        assert result[0].title == "Starlight"
        assert result[0].artist == "Muse"
        assert spotify.tracks.received_query == "muse"
        assert spotify.tracks.received_limit == 10

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
        assert result[0].genres == ("alternative rock", "rock")
        assert result[0].followers == 1234567
        assert result[0].popularity == 91
        assert result[0].image_url == "https://example.com/muse.jpg"
        assert spotify.artists.received_query == "muse"
        assert spotify.artists.received_limit == 10

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

        assert result.tracks == ()
        assert result.playlists == ()
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

        assert result.tracks == ()
        assert result.playlists == ()
        assert result.artists == ()
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

        assert first_result.tracks == ()
        assert first_result.playlists == ()
        assert first_result.artists == ()
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
            return SpotifyUnifiedSearchResult(tracks=(), playlists=(), artists=())

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

        assert result == SpotifyUnifiedSearchResult(tracks=(), playlists=(), artists=())
        assert spotify.retry_hook_callback is None
        assert "Retrying Spotifyify request" in caplog.text
        assert "path=/search" in caplog.text
        assert "status_code=429" in caplog.text


class TestSpotifyPlaylistCreator:
    def test_create_private_playlist_uses_user_token_flow(self) -> None:
        spotify = _PlaylistCreatorSpotifyStub()
        service = _make_playlist_creator(cast(Any, spotify))

        playlist_id = asyncio.run(
            service.create_private_playlist(
                access_token="token-123",
                name="Roadtrip",
                description="Late night drive",
            )
        )

        assert playlist_id == "playlist-1"
        assert spotify.playlists.calls == [
            (
                "create",
                ("Roadtrip",),
                {
                    "public": False,
                    "collaborative": False,
                    "description": "Late night drive",
                    "user_id": None,
                },
            ),
        ]
        assert len(spotify.session_calls) == 1
        assert spotify.session_calls[0][0] == "token-123"
        assert callable(spotify.session_calls[0][1])

    def test_update_playlist_and_replace_tracks_use_user_token(self) -> None:
        spotify = _PlaylistCreatorSpotifyStub()
        service = _make_playlist_creator(cast(Any, spotify))

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

        assert spotify.playlists.calls == [
            (
                "update",
                ("playlist-1",),
                {
                    "name": "Updated",
                    "public": None,
                    "collaborative": None,
                    "description": "Updated description",
                },
            ),
            (
                "replace",
                ("playlist-1", ["spotify:track:1", "spotify:track:2"]),
                {},
            ),
        ]
        assert [session_call[0] for session_call in spotify.session_calls] == [
            "token-123",
            "token-123",
        ]
        assert all(callable(session_call[1]) for session_call in spotify.session_calls)


class TestSpotifyClientContract:
    def test_search_pages_within_development_mode_limit(self) -> None:
        requested_limits: list[int] = []
        transport = httpx2.MockTransport(_paged_track_search(40, requested_limits))

        async def _run() -> list[SpotifyTrack]:
            async with SpotifyClient(
                token_provider=_AppTokenProvider(),
                transport=transport,
            ) as spotify:
                return await _make_search(spotify)._search_tracks(
                    query="muse",
                    limit=25,
                )

        result = asyncio.run(_run())

        assert [track.id for track in result] == [
            f"track{index}" for index in range(25)
        ]
        assert result[0].year == 2001
        assert requested_limits == [10, 10, 10]

    def test_get_track_returns_none_for_malformed_id_without_request(self) -> None:
        requests: list[httpx2.Request] = []

        def handle(request: httpx2.Request) -> httpx2.Response:
            requests.append(request)
            return httpx2.Response(200, json=_track_payload(1))

        async def _run() -> SpotifyTrack | None:
            async with SpotifyClient(
                token_provider=_AppTokenProvider(),
                transport=httpx2.MockTransport(handle),
            ) as spotify:
                return await _make_search(spotify).get_track_by_id(
                    track_id="bad id",
                )

        assert asyncio.run(_run()) is None
        assert requests == []

    def test_playlist_export_uses_user_token_on_current_routes(self) -> None:
        requests: list[tuple[str, str, str | None]] = []

        def handle(request: httpx2.Request) -> httpx2.Response:
            requests.append(
                (
                    request.method,
                    request.url.path,
                    request.headers.get("Authorization"),
                )
            )
            if request.method == "POST":
                return httpx2.Response(
                    201,
                    json={"id": "playlist1", "type": "playlist", "name": "Roadtrip"},
                )
            return httpx2.Response(200, json={"snapshot_id": "snapshot1"})

        async def _run() -> str:
            async with SpotifyClient(
                token_provider=_AppTokenProvider(),
                transport=httpx2.MockTransport(handle),
            ) as spotify:
                creator = SpotifyPlaylistCreator(spotify=spotify)
                playlist_id = await creator.create_private_playlist(
                    access_token="user-token",
                    name="Roadtrip",
                    description="Late night drive",
                )
                await creator.replace_playlist_tracks(
                    access_token="user-token",
                    playlist_id=playlist_id,
                    track_uris=["spotify:track:track1"],
                )
                return playlist_id

        assert asyncio.run(_run()) == "playlist1"
        assert requests == [
            ("POST", "/v1/me/playlists", "Bearer user-token"),
            ("PUT", "/v1/playlists/playlist1/items", "Bearer user-token"),
        ]
