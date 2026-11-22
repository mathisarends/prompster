from typing import Any

import httpx2
import pytest
from spotifyify import SpotifyClient

from agent.tools.handler.spotify import Spotify
from agent.tools.params import PlaylistIdParams, SearchParams


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


def _paging(
    *,
    items: list[Any],
    limit: int,
    offset: int,
    total: int,
) -> dict[str, Any]:
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


def _search_params(limit: int) -> SearchParams:
    return SearchParams(query="a-ha", limit=limit)


class TestSpotifyClientContract:
    @pytest.mark.asyncio
    async def test_search_tracks_pages_within_development_mode_limit(self) -> None:
        requested_limits: list[int] = []

        def handle(request: httpx2.Request) -> httpx2.Response:
            limit = int(request.url.params["limit"])
            offset = int(request.url.params["offset"])
            requested_limits.append(limit)
            items = [
                _track_payload(index)
                for index in range(offset, min(offset + limit, 40))
            ]
            return httpx2.Response(
                200,
                json={
                    "tracks": _paging(
                        items=items,
                        limit=limit,
                        offset=offset,
                        total=40,
                    )
                },
            )

        async with SpotifyClient(
            token_provider=_AppTokenProvider(),
            transport=httpx2.MockTransport(handle),
        ) as client:
            result = await Spotify(client=client).search_tracks(_search_params(25))

        assert len(result.tracks) == 25
        assert result.tracks[24].spotify_uri == "spotify:track:track24"
        assert requested_limits == [10, 10, 10]

    @pytest.mark.asyncio
    async def test_playlist_tracks_use_legacy_route_with_app_token(self) -> None:
        paths: list[str] = []
        token_provider = _AppTokenProvider()

        def handle(request: httpx2.Request) -> httpx2.Response:
            paths.append(request.url.path)
            return httpx2.Response(
                200,
                json=_paging(
                    items=[{"track": _track_payload(1)}],
                    limit=50,
                    offset=0,
                    total=1,
                ),
            )

        async with SpotifyClient(
            token_provider=token_provider,
            transport=httpx2.MockTransport(handle),
        ) as client:
            result = await Spotify(client=client).get_playlist_tracks(
                PlaylistIdParams(
                    playlist_id="spotify:playlist:playlist1",
                    playlist_name="All Out 80s",
                )
            )

        assert paths == ["/v1/playlists/playlist1/tracks"]
        assert token_provider.require_user_calls == [False]
        assert [track.spotify_uri for track in result.tracks] == [
            "spotify:track:track1"
        ]

    @pytest.mark.asyncio
    async def test_playlist_tracks_reject_path_traversal_without_request(self) -> None:
        requests: list[httpx2.Request] = []

        def handle(request: httpx2.Request) -> httpx2.Response:
            requests.append(request)
            return httpx2.Response(200, json={})

        async with SpotifyClient(
            token_provider=_AppTokenProvider(),
            transport=httpx2.MockTransport(handle),
        ) as client:
            with pytest.raises(ValueError, match="Expected a nonempty Spotify ID"):
                await Spotify(client=client).get_playlist_tracks(
                    PlaylistIdParams(
                        playlist_id="../me",
                        playlist_name="All Out 80s",
                    )
                )

        assert requests == []

    @pytest.mark.asyncio
    async def test_closing_handler_keeps_shared_client_usable(self) -> None:
        def handle(request: httpx2.Request) -> httpx2.Response:
            return httpx2.Response(
                200,
                json={
                    "tracks": _paging(
                        items=[_track_payload(1)],
                        limit=1,
                        offset=0,
                        total=1,
                    )
                },
            )

        async with SpotifyClient(
            token_provider=_AppTokenProvider(),
            transport=httpx2.MockTransport(handle),
        ) as client:
            first_run = Spotify(client=client)
            await first_run.search_tracks(_search_params(1))
            await first_run.close()

            second_run = Spotify(client=client)
            result = await second_run.search_tracks(_search_params(1))

        assert len(result.tracks) == 1
