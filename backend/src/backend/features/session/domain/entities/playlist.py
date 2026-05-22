from datetime import datetime
from uuid import UUID

from backend.shared.ddd import Entity


class PlaylistTrack(Entity):
    def __init__(
        self,
        title: str,
        artist: str,
        year: int | None = None,
        spotify_uri: str | None = None,
        cover_url: str | None = None,
        id: UUID | None = None,
        created_time: datetime | None = None,
    ) -> None:
        super().__init__(id=id, created_time=created_time)
        self.title = title
        self.artist = artist
        self.year = year
        self.spotify_uri = spotify_uri
        self.cover_url = cover_url


class Playlist(Entity):
    def __init__(
        self,
        tracks: list[PlaylistTrack],
        name: str | None = None,
        id: UUID | None = None,
        created_time: datetime | None = None,
    ) -> None:
        super().__init__(id=id, created_time=created_time)
        self.tracks = tracks
        self.name = name
