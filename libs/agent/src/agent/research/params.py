from pydantic import BaseModel, Field


class SearchParams(BaseModel):
    query: str = Field(description="Spotify search query.")
    limit: int = Field(default=10, ge=1, le=50, description="Maximum results.")


class PlaylistIdParams(BaseModel):
    playlist_id: str = Field(description="Spotify playlist URI or ID.")
    playlist_name: str = Field(
        description=(
            "Readable playlist name from the search result, shown in the UI. "
            "Never the playlist ID."
        ),
    )
    offset: int = Field(
        default=0,
        ge=0,
        description="Zero-based page offset. Start at 0.",
    )
