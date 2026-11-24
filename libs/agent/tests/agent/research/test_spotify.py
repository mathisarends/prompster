from typing import Any

import httpx2
import pytest
from agent.research import Spotify
from spotifyify import SpotifyClient


class _AppTokenProvider:
    def __init__(self) -> None:
        self.require_user_calls: list[bool] = []

    async def get_access_token(
        self,
        require_user: bool,
        scope: str | list[str] | tuple[str, ...] | None = None,
    ) -> str:
        self.require_user_calls.append(require_user)
        return "app-token"


def _track_payload(index: int) -> dict[str, Any]:
    return {
        "id": f"track{index}",
        "name": f"Track {index}",
        "type": "track",
        "uri": f"spotify:track:track{index}",
        "artists": [{"name": "a-ha"}],
        "album": {
            "album_type": "album",
            "total_tracks": 1,
            "external_urls": {},
            "href": "https://api.spotify.com/v1/albums/album1",
            "id": "album1",
            "images": [],
            "name": "Hunting High and Low",
            "release_date": "1985-06-01",
            "release_date_precision": "day",
            "type": "album",
            "uri": "spotify:album:album1",
            "artists": [],
        },
    }


def _paging(*, items: list[Any], limit: int, offset: int, total: int) -> dict[str, Any]:
    end = offset + limit
    return {
        "href": "https://api.spotify.com/v1/resource",
        "limit": limit,
        "offset": offset,
        "total": total,
        "next": (
            f"https://api.spotify.com/v1/resource?offset={end}&limit={limit}"
            if end < total
            else None
        ),
        "previous": None,
        "items": items,
    }


def _client(handle: Any, tokens: _AppTokenProvider | None = None) -> SpotifyClient:
    return SpotifyClient(
        token_provider=tokens or _AppTokenProvider(),
        transport=httpx2.MockTransport(handle),
    )


def _track_search(request: httpx2.Request, total: int) -> httpx2.Response:
    limit = int(request.url.params["limit"])
    offset = int(request.url.params["offset"])
    items = [_track_payload(i) for i in range(offset, min(offset + limit, total))]
    page = _paging(items=items, limit=limit, offset=offset, total=total)
    return httpx2.Response(200, json={"tracks": page})


@pytest.mark.asyncio
async def test_search_tracks_pages_within_the_development_mode_limit() -> None:
    limits: list[int] = []

    def handle(request: httpx2.Request) -> httpx2.Response:
        limits.append(int(request.url.params["limit"]))
        return _track_search(request, total=40)

    async with _client(handle) as client:
        result = await Spotify(client).search_tracks("a-ha", limit=25)

    assert len(result.tracks) == 25
    assert result.tracks[24].uri == "spotify:track:track24"
    assert limits == [10, 10, 10]


@pytest.mark.asyncio
async def test_track_results_render_one_tag_per_addable_track() -> None:
    async with _client(lambda request: _track_search(request, total=1)) as client:
        result = await Spotify(client).search_tracks("a-ha", limit=1)

    assert result.content == (
        '<track uri="spotify:track:track0" label="a-ha - Track 0 (1985)" />'
    )
    assert result.tracks[0].year == 1985


@pytest.mark.asyncio
async def test_playlist_tracks_use_the_legacy_route_with_an_app_token() -> None:
    paths: list[str] = []
    tokens = _AppTokenProvider()

    def handle(request: httpx2.Request) -> httpx2.Response:
        paths.append(request.url.path)
        page = _paging(
            items=[{"track": _track_payload(1)}], limit=50, offset=0, total=1
        )
        return httpx2.Response(200, json=page)

    async with _client(handle, tokens) as client:
        result = await Spotify(client).get_playlist_tracks("spotify:playlist:playlist1")

    assert paths == ["/v1/playlists/playlist1/tracks"]
    assert tokens.require_user_calls == [False]
    assert [track.uri for track in result.tracks] == ["spotify:track:track1"]


@pytest.mark.asyncio
async def test_playlist_tracks_reject_path_traversal_without_a_request() -> None:
    requests: list[httpx2.Request] = []

    def handle(request: httpx2.Request) -> httpx2.Response:
        requests.append(request)
        return httpx2.Response(200, json={})

    async with _client(handle) as client:
        with pytest.raises(ValueError, match="Expected a nonempty Spotify ID"):
            await Spotify(client).get_playlist_tracks("../me")

    assert requests == []


@pytest.mark.asyncio
async def test_closing_keeps_a_shared_client_usable() -> None:
    async with _client(lambda request: _track_search(request, total=1)) as client:
        first = Spotify(client)
        await first.search_tracks("a-ha", limit=1)
        await first.close()

        result = await Spotify(client).search_tracks("a-ha", limit=1)

    assert len(result.tracks) == 1
