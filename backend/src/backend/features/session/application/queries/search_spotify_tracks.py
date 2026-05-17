from backend.features.session.application.ports.spotify_track_search import (
    SpotifyTrack,
    SpotifyTrackSearch,
)


class SearchSpotifyTracksHandler:
    def __init__(self, spotify_track_search: SpotifyTrackSearch) -> None:
        self._spotify_track_search = spotify_track_search

    async def handle(self, *, query: str, limit: int = 20) -> list[SpotifyTrack]:
        return await self._spotify_track_search.search(query=query, limit=limit)
