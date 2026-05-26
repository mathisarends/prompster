from datetime import datetime
from uuid import UUID

from backend.shared.ddd import Entity


_MIN_TRACK_YEAR = 1900
_MAX_TRACK_YEAR = 2100


class PlaylistTrack(Entity):
    def __init__(
        self,
        title: str,
        artist: str,
        year: int,
        spotify_uri: str | None = None,
        cover_url: str | None = None,
        is_pinned: bool = False,
        id: UUID | None = None,
        created_time: datetime | None = None,
    ) -> None:
        super().__init__(id=id, created_time=created_time)
        if year < _MIN_TRACK_YEAR or year > _MAX_TRACK_YEAR:
            raise ValueError(
                f"year must be between {_MIN_TRACK_YEAR} and {_MAX_TRACK_YEAR}."
            )

        self.title = title
        self.artist = artist
        self.year = year
        self.spotify_uri = spotify_uri
        self.cover_url = cover_url
        self.is_pinned = is_pinned


class Playlist(Entity):
    def __init__(
        self,
        tracks: list[PlaylistTrack],
        name: str | None = None,
        spotify_playlist_id: str | None = None,
        id: UUID | None = None,
        created_time: datetime | None = None,
    ) -> None:
        super().__init__(id=id, created_time=created_time)
        self.tracks = tracks
        self.name = name
        self.spotify_playlist_id = spotify_playlist_id
