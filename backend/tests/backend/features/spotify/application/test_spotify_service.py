import asyncio
from types import SimpleNamespace
from typing import Any, cast

from backend.features.spotify.application import SpotifySearchType
from backend.features.spotify.infrastructure.spotify_service import SpotifyService


class _TracksStub:
    def __init__(self, items: list[SimpleNamespace]) -> None:
        self._items = items
        self.received_query: str | None = None
        self.received_limit: int | None = None

    async def find(self, query: str, *, limit: int) -> SimpleNamespace:
        self.received_query = query
        self.received_limit = limit
        return SimpleNamespace(items=self._items)


class _ArtistsStub:
    def __init__(self, items: list[SimpleNamespace]) -> None:
        self._items = items
        self.received_query: str | None = None
        self.received_limit: int | None = None

    async def find(self, query: str, *, limit: int) -> SimpleNamespace:
        self.received_query = query
        self.received_limit = limit
        return SimpleNamespace(items=self._items)


class _PlaylistsStub:
    def __init__(self, items: list[SimpleNamespace]) -> None:
        self._items = items
        self.received_query: str | None = None
        self.received_limit: int | None = None

    async def find(self, query: str, *, limit: int) -> SimpleNamespace:
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


class TestSpotifyService:
    def test_search_tracks_uses_default_limit(self) -> None:
        spotify = _SpotifyStub(track_items=[_make_track()])
        service = SpotifyService(spotify=cast(Any, spotify))

        result = asyncio.run(service._search_tracks(query="muse"))

        assert len(result) == 1
        assert result[0].title == "Starlight"
        assert result[0].artist == "Muse"
        assert spotify.tracks.received_query == "muse"
        assert spotify.tracks.received_limit == 20

    def test_search_tracks_uses_explicit_limit(self) -> None:
        spotify = _SpotifyStub(track_items=[_make_track()])
        service = SpotifyService(spotify=cast(Any, spotify))

        result = asyncio.run(service._search_tracks(query="muse", limit=7))

        assert len(result) == 1
        assert spotify.tracks.received_query == "muse"
        assert spotify.tracks.received_limit == 7

    def test_search_tracks_short_circuits_blank_query(self) -> None:
        spotify = _SpotifyStub(track_items=[_make_track()])
        service = SpotifyService(spotify=cast(Any, spotify))

        result = asyncio.run(service._search_tracks(query="   "))

        assert result == []
        assert spotify.tracks.received_query is None
        assert spotify.tracks.received_limit is None

    def test_search_artists_uses_default_limit(self) -> None:
        spotify = _SpotifyStub(artist_items=[_make_artist()])
        service = SpotifyService(spotify=cast(Any, spotify))

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
        service = SpotifyService(spotify=cast(Any, spotify))

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
        service = SpotifyService(spotify=cast(Any, spotify))

        result = asyncio.run(
            service.search_unified(
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
        service = SpotifyService(spotify=cast(Any, spotify))

        result = asyncio.run(service.search_unified(query="muse"))

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
        service = SpotifyService(spotify=cast(Any, spotify))

        result = asyncio.run(service.search_unified(query="  "))

        assert result.tracks == []
        assert result.playlists == []
        assert result.artists == []
        assert spotify.tracks.received_query is None
        assert spotify.playlists.received_query is None
        assert spotify.artists.received_query is None
