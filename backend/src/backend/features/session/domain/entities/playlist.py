from datetime import UTC, datetime
from typing import Self
from uuid import UUID, uuid4

from backend.shared.ddd import Entity


_MIN_TRACK_YEAR = 1900
_MAX_TRACK_YEAR = 2100


class PlaylistTrack(Entity):
    def __init__(
        self,
        *,
        id: UUID,
        created_at: datetime,
        title: str,
        artist: str,
        year: int,
        spotify_uri: str | None = None,
        cover_url: str | None = None,
    ) -> None:
        super().__init__(id=id, created_at=created_at)
        if year < _MIN_TRACK_YEAR or year > _MAX_TRACK_YEAR:
            raise ValueError(
                f"year must be between {_MIN_TRACK_YEAR} and {_MAX_TRACK_YEAR}."
            )

        self.title = title
        self.artist = artist
        self.year = year
        self.spotify_uri = spotify_uri
        self.cover_url = cover_url

    @classmethod
    def create(
        cls,
        *,
        title: str,
        artist: str,
        year: int,
        spotify_uri: str | None = None,
        cover_url: str | None = None,
    ) -> Self:
        return cls(
            id=uuid4(),
            created_at=datetime.now(UTC),
            title=title,
            artist=artist,
            year=year,
            spotify_uri=spotify_uri,
            cover_url=cover_url,
        )

    @classmethod
    def restore(
        cls,
        *,
        id: UUID,
        created_at: datetime,
        title: str,
        artist: str,
        year: int,
        spotify_uri: str | None = None,
        cover_url: str | None = None,
    ) -> Self:
        return cls(
            id=id,
            created_at=created_at,
            title=title,
            artist=artist,
            year=year,
            spotify_uri=spotify_uri,
            cover_url=cover_url,
        )


class Playlist(Entity):
    def __init__(
        self,
        *,
        id: UUID,
        created_at: datetime,
        tracks: list[PlaylistTrack],
        name: str | None = None,
        spotify_playlist_id: str | None = None,
    ) -> None:
        super().__init__(id=id, created_at=created_at)
        self.tracks = tracks
        self.name = name
        self.spotify_playlist_id = spotify_playlist_id

    @classmethod
    def create(
        cls,
        *,
        tracks: list[PlaylistTrack],
        name: str | None = None,
        spotify_playlist_id: str | None = None,
    ) -> Self:
        return cls(
            id=uuid4(),
            created_at=datetime.now(UTC),
            tracks=tracks,
            name=name,
            spotify_playlist_id=spotify_playlist_id,
        )

    @classmethod
    def restore(
        cls,
        *,
        id: UUID,
        created_at: datetime,
        tracks: list[PlaylistTrack],
        name: str | None = None,
        spotify_playlist_id: str | None = None,
    ) -> Self:
        return cls(
            id=id,
            created_at=created_at,
            tracks=tracks,
            name=name,
            spotify_playlist_id=spotify_playlist_id,
        )
