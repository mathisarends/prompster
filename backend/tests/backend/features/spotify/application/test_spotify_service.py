import asyncio
from types import SimpleNamespace
from typing import Any, cast

from backend.features.spotify.application import SpotifyService
from backend.features.spotify.infrastructure.spotify_service import SpotifyifyService


class _TracksStub:
    def __init__(self, items: list[SimpleNamespace]) -> None:
        self._items = items
        self.received_query: str | None = None
        self.received_limit: int | None = None

    async def find(self, query: str, *, limit: int) -> SimpleNamespace:
        self.received_query = query
        self.received_limit = limit
        return SimpleNamespace(items=self._items)


class _SpotifyStub:
    def __init__(self, items: list[SimpleNamespace]) -> None:
        self.tracks = _TracksStub(items=items)


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
        preview_url="https://example.com/preview.mp3",
    )


class TestSpotifyifyService:
    def test_search_tracks_uses_default_limit(self) -> None:
        spotify = _SpotifyStub(items=[_make_track()])
        service: SpotifyService = SpotifyifyService(spotify=cast(Any, spotify))

        result = asyncio.run(service.search_tracks(query="muse"))

        assert len(result) == 1
        assert result[0].title == "Starlight"
        assert result[0].artist == "Muse"
        assert spotify.tracks.received_query == "muse"
        assert spotify.tracks.received_limit == 20

    def test_search_tracks_uses_explicit_limit(self) -> None:
        spotify = _SpotifyStub(items=[_make_track()])
        service: SpotifyService = SpotifyifyService(spotify=cast(Any, spotify))

        result = asyncio.run(service.search_tracks(query="muse", limit=7))

        assert len(result) == 1
        assert spotify.tracks.received_query == "muse"
        assert spotify.tracks.received_limit == 7

    def test_search_tracks_short_circuits_blank_query(self) -> None:
        spotify = _SpotifyStub(items=[_make_track()])
        service: SpotifyService = SpotifyifyService(spotify=cast(Any, spotify))

        result = asyncio.run(service.search_tracks(query="   "))

        assert result == []
        assert spotify.tracks.received_query is None
        assert spotify.tracks.received_limit is None
