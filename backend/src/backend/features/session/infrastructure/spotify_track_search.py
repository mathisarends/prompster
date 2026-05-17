from backend.features.session.application.ports.spotify_track_search import (
    SpotifyTrack,
    SpotifyTrackSearch,
)

_MOCK_TRACKS: list[SpotifyTrack] = [
    SpotifyTrack(
        id="3n3Ppam7vgaVa1iaRUc9Lp",
        title="Mr. Brightside",
        artist="The Killers",
        album="Hot Fuss",
        year=2004,
        cover_url="https://i.scdn.co/image/ab67616d0000b2730b51f8d91f3a21e8426361ae",
        preview_url=None,
    ),
    SpotifyTrack(
        id="7qiZfU4dY1lWllzX7mPBI3",
        title="Shape of You",
        artist="Ed Sheeran",
        album="÷ (Divide)",
        year=2017,
        cover_url="https://i.scdn.co/image/ab67616d0000b273ba5db46f4b838ef6027e6f96",
        preview_url=None,
    ),
    SpotifyTrack(
        id="0VjIjW4GlUZAMYd2vXMi3b",
        title="Blinding Lights",
        artist="The Weeknd",
        album="After Hours",
        year=2020,
        cover_url="https://i.scdn.co/image/ab67616d0000b2738863bc11d2aa12b54f5aeb36",
        preview_url=None,
    ),
    SpotifyTrack(
        id="4iV5W9uYEdYUVa79Axb7Rh",
        title="One Dance",
        artist="Drake",
        album="Views",
        year=2016,
        cover_url="https://i.scdn.co/image/ab67616d0000b2739416ed64daf84936d89e671c",
        preview_url=None,
    ),
    SpotifyTrack(
        id="6habFhsOp2NvshLv26DqMb",
        title="Despacito",
        artist="Luis Fonsi",
        album="VIDA",
        year=2017,
        cover_url="https://i.scdn.co/image/ab67616d0000b2734a3a4d3b9b9bb89c0d3a8f51",
        preview_url=None,
    ),
]


class MockSpotifyTrackSearch(SpotifyTrackSearch):
    async def search(self, *, query: str, limit: int = 20) -> list[SpotifyTrack]:
        needle = query.strip().lower()
        if not needle:
            return _MOCK_TRACKS[:limit]
        matches = [
            track
            for track in _MOCK_TRACKS
            if needle in track.title.lower() or needle in track.artist.lower()
        ]
        return matches[:limit] if matches else _MOCK_TRACKS[:limit]
