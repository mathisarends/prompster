import asyncio

from backend.features.session.application.ports.spotify_track_search import (
    SpotifyTrack,
    SpotifyTrackSearch,
)
from backend.features.session.application.queries.search_spotify_tracks import (
    SearchSpotifyTracksHandler,
)


class _SpotifyTrackSearchStub(SpotifyTrackSearch):
    def __init__(self, tracks: list[SpotifyTrack]) -> None:
        self._tracks = tracks
        self.received_query: str | None = None
        self.received_limit: int | None = None

    async def search(self, *, query: str, limit: int = 20) -> list[SpotifyTrack]:
        self.received_query = query
        self.received_limit = limit
        return self._tracks


class TestSearchSpotifyTracksHandler:
    def test_handle_uses_default_limit(self) -> None:
        tracks = [SpotifyTrack(id="1", title="Starlight", artist="Muse")]
        search = _SpotifyTrackSearchStub(tracks=tracks)
        handler = SearchSpotifyTracksHandler(spotify_track_search=search)

        result = asyncio.run(handler.handle(query="muse"))

        assert result == tracks
        assert search.received_query == "muse"
        assert search.received_limit == 20

    def test_handle_uses_explicit_limit(self) -> None:
        tracks = [SpotifyTrack(id="1", title="Starlight", artist="Muse")]
        search = _SpotifyTrackSearchStub(tracks=tracks)
        handler = SearchSpotifyTracksHandler(spotify_track_search=search)

        result = asyncio.run(handler.handle(query="muse", limit=7))

        assert result == tracks
        assert search.received_query == "muse"
        assert search.received_limit == 7
