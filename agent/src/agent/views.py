from pydantic import BaseModel, Field


class SearchParams(BaseModel):
    query: str = Field(description="Search query.")
    limit: int = Field(default=10, description="Maximum number of results.")


class ArtistAlbumsParams(BaseModel):
    artist_id: str = Field(description="Spotify artist URI or ID.")
    include_groups: str = Field(
        default="album,single",
        description="Album groups to include, comma-separated.",
    )
    limit: int = Field(default=20, description="Maximum number of albums.")


class ArtistTopTracksParams(BaseModel):
    artist_id: str = Field(description="Spotify artist URI or ID.")
    country: str = Field(default="DE", description="ISO country code.")


class AlbumTracksParams(BaseModel):
    album_id: str = Field(description="Spotify album URI or ID.")


class CreatePlaylistParams(BaseModel):
    name: str = Field(description="Name of the playlist to create.")
    description: str = Field(default="", description="Playlist description.")


class PlaylistTracksMutationParams(BaseModel):
    playlist_id: str = Field(description="Spotify playlist ID.")
    track_uris: list[str] = Field(description="Spotify track URIs.")


class PlaylistIdParams(BaseModel):
    playlist_id: str = Field(description="Spotify playlist ID.")


class GenerateCardsParams(BaseModel):
    playlist_id: str = Field(description="Spotify playlist ID.")
