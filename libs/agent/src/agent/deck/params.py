from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TrackRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    uri: str = Field(description="Spotify track URI, e.g. spotify:track:...")

    @field_validator("uri")
    @classmethod
    def require_track_uri(cls, value: str) -> str:
        return _require_track_uri(value)


class TrackRefReplacement(BaseModel):
    old_id: UUID
    new_uri: str = Field(description="Spotify track URI, e.g. spotify:track:...")

    @field_validator("new_uri")
    @classmethod
    def require_track_uri(cls, value: str) -> str:
        return _require_track_uri(value)


class AddDeckTracksParams(BaseModel):
    tracks: list[TrackRef] = Field(
        min_length=1,
        description="Spotify track URIs from search or playlist results.",
    )


class RemoveDeckTracksParams(BaseModel):
    track_ids: list[UUID] = Field(
        min_length=1,
        description="Track IDs from the current deck state.",
    )


class ReplaceDeckTracksParams(BaseModel):
    replacements: list[TrackRefReplacement] = Field(
        min_length=1,
        description="Deck track IDs to swap for Spotify track URIs.",
    )


def _require_track_uri(value: str) -> str:
    if not value.startswith("spotify:track:"):
        raise ValueError("uri must start with 'spotify:track:'")
    return value
