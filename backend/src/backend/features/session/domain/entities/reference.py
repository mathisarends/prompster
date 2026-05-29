from datetime import datetime
from uuid import UUID

from backend.shared.ddd import Entity


class PlaylistReference(Entity):
    """A Spotify playlist referenced as source material for a session."""

    def __init__(
        self,
        spotify_playlist_id: str,
        name: str,
        owner: str | None = None,
        cover_url: str | None = None,
        total_tracks: int | None = None,
        id: UUID | None = None,
        created_time: datetime | None = None,
    ) -> None:
        super().__init__(id=id, created_time=created_time)
        self.spotify_playlist_id = spotify_playlist_id
        self.name = name
        self.owner = owner
        self.cover_url = cover_url
        self.total_tracks = total_tracks


class ArtistReference(Entity):
    """A Spotify artist referenced as source material for a session."""

    def __init__(
        self,
        spotify_artist_id: str,
        name: str,
        image_url: str | None = None,
        genres: tuple[str, ...] = (),
        followers: int | None = None,
        popularity: int | None = None,
        id: UUID | None = None,
        created_time: datetime | None = None,
    ) -> None:
        super().__init__(id=id, created_time=created_time)
        self.spotify_artist_id = spotify_artist_id
        self.name = name
        self.image_url = image_url
        self.genres = tuple(genres)
        self.followers = followers
        self.popularity = popularity
