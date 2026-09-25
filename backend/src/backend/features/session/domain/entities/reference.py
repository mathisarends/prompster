from datetime import UTC, datetime
from typing import Self
from uuid import UUID, uuid4

from backend.shared.ddd import Entity


class PlaylistReference(Entity):
    """A Spotify playlist referenced as source material for a session."""

    def __init__(
        self,
        *,
        id: UUID,
        created_at: datetime,
        spotify_playlist_id: str,
        name: str,
        owner: str | None = None,
        cover_url: str | None = None,
        total_tracks: int | None = None,
    ) -> None:
        super().__init__(id=id, created_time=created_at)
        self.spotify_playlist_id = spotify_playlist_id
        self.name = name
        self.owner = owner
        self.cover_url = cover_url
        self.total_tracks = total_tracks

    @classmethod
    def create(
        cls,
        *,
        spotify_playlist_id: str,
        name: str,
        owner: str | None = None,
        cover_url: str | None = None,
        total_tracks: int | None = None,
    ) -> Self:
        return cls(
            id=uuid4(),
            created_at=datetime.now(UTC),
            spotify_playlist_id=spotify_playlist_id,
            name=name,
            owner=owner,
            cover_url=cover_url,
            total_tracks=total_tracks,
        )

    @classmethod
    def restore(
        cls,
        *,
        id: UUID,
        created_at: datetime,
        spotify_playlist_id: str,
        name: str,
        owner: str | None = None,
        cover_url: str | None = None,
        total_tracks: int | None = None,
    ) -> Self:
        return cls(
            id=id,
            created_at=created_at,
            spotify_playlist_id=spotify_playlist_id,
            name=name,
            owner=owner,
            cover_url=cover_url,
            total_tracks=total_tracks,
        )


class ArtistReference(Entity):
    """A Spotify artist referenced as source material for a session."""

    def __init__(
        self,
        *,
        id: UUID,
        created_at: datetime,
        spotify_artist_id: str,
        name: str,
        image_url: str | None = None,
        genres: tuple[str, ...] = (),
        followers: int | None = None,
        popularity: int | None = None,
    ) -> None:
        super().__init__(id=id, created_time=created_at)
        self.spotify_artist_id = spotify_artist_id
        self.name = name
        self.image_url = image_url
        self.genres = tuple(genres)
        self.followers = followers
        self.popularity = popularity

    @classmethod
    def create(
        cls,
        *,
        spotify_artist_id: str,
        name: str,
        image_url: str | None = None,
        genres: tuple[str, ...] = (),
        followers: int | None = None,
        popularity: int | None = None,
    ) -> Self:
        return cls(
            id=uuid4(),
            created_at=datetime.now(UTC),
            spotify_artist_id=spotify_artist_id,
            name=name,
            image_url=image_url,
            genres=genres,
            followers=followers,
            popularity=popularity,
        )

    @classmethod
    def restore(
        cls,
        *,
        id: UUID,
        created_at: datetime,
        spotify_artist_id: str,
        name: str,
        image_url: str | None = None,
        genres: tuple[str, ...] = (),
        followers: int | None = None,
        popularity: int | None = None,
    ) -> Self:
        return cls(
            id=id,
            created_at=created_at,
            spotify_artist_id=spotify_artist_id,
            name=name,
            image_url=image_url,
            genres=genres,
            followers=followers,
            popularity=popularity,
        )
