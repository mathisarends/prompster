from pydantic import BaseModel, Field


class SearchParams(BaseModel):
    query: str
    limit: int = 10


class ArtistAlbumsParams(BaseModel):
    artist_id: str = Field(description="URI or ID.")
    include_groups: str = Field(default="album,single", description="Comma-separated.")
    limit: int = 20


class ArtistTopTracksParams(BaseModel):
    artist_id: str = Field(description="URI or ID.")
    country: str = Field(default="DE", description="ISO 3166-1 alpha-2.")


class AlbumTracksParams(BaseModel):
    album_id: str = Field(description="URI or ID.")


class CreatePlaylistParams(BaseModel):
    name: str
    description: str = ""


class PlaylistTracksMutationParams(BaseModel):
    playlist_id: str
    track_uris: list[str]


class PlaylistIdParams(BaseModel):
    playlist_id: str


class GenerateCardsParams(BaseModel):
    playlist_id: str


class AskFollowUpOption(BaseModel):
    label: str


class AskFollowUpQuestion(BaseModel):
    question: str
    options: list[AskFollowUpOption] = Field(min_length=1, max_length=4)


class AskFollowUpParams(BaseModel):
    questions: list[AskFollowUpQuestion] = Field(min_length=1, max_length=4)
