from enum import StrEnum
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TrackRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    uri: str = Field(description="Spotify track URI, e.g. spotify:track:...")

    @field_validator("uri")
    @classmethod
    def require_track_uri(cls, value: str) -> str:
        if not value.startswith("spotify:track:"):
            raise ValueError("uri must start with 'spotify:track:'")
        return value


class TrackRefReplacement(BaseModel):
    old_id: UUID
    new_uri: str = Field(description="Spotify track URI, e.g. spotify:track:...")

    @field_validator("new_uri")
    @classmethod
    def require_track_uri(cls, value: str) -> str:
        if not value.startswith("spotify:track:"):
            raise ValueError("new_uri must start with 'spotify:track:'")
        return value


class DeckDraftTrack(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    title: str = Field(description="Track title.")
    artist: str = Field(description="Primary artist or comma-separated artists.")
    year: int | None = Field(default=None, description="Release year.")
    spotify_uri: str | None = Field(
        default=None,
        description="Spotify track URI, e.g. spotify:track:...",
    )
    cover_url: str | None = Field(default=None, description="Album cover image URL.")

    @field_validator("spotify_uri")
    @classmethod
    def require_track_uri(cls, value: str | None) -> str | None:
        if value is not None and not value.startswith("spotify:track:"):
            raise ValueError("spotify_uri must start with 'spotify:track:'")
        return value


class DeckDraft(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    tracks: list[DeckDraftTrack]


class DeckDraftUpdateKind(StrEnum):
    CREATED = "created"
    REPLACED = "replaced"
    TRACKS_ADDED = "tracks_added"
    TRACKS_REMOVED = "tracks_removed"
    TRACKS_REPLACED = "tracks_replaced"


class DeckDraftCreated(BaseModel):
    kind: Literal[DeckDraftUpdateKind.CREATED] = DeckDraftUpdateKind.CREATED
    deck_draft: DeckDraft


class DeckDraftReplaced(BaseModel):
    kind: Literal[DeckDraftUpdateKind.REPLACED] = DeckDraftUpdateKind.REPLACED
    deck_draft: DeckDraft


class DeckDraftTracksAdded(BaseModel):
    kind: Literal[DeckDraftUpdateKind.TRACKS_ADDED] = DeckDraftUpdateKind.TRACKS_ADDED
    deck_draft: DeckDraft
    tracks: list[DeckDraftTrack]


class DeckDraftTracksRemoved(BaseModel):
    kind: Literal[DeckDraftUpdateKind.TRACKS_REMOVED] = (
        DeckDraftUpdateKind.TRACKS_REMOVED
    )
    deck_draft: DeckDraft
    track_ids: list[UUID]


class DeckDraftTrackReplacement(BaseModel):
    track_id: UUID
    track: DeckDraftTrack


class DeckDraftTracksReplaced(BaseModel):
    kind: Literal[DeckDraftUpdateKind.TRACKS_REPLACED] = (
        DeckDraftUpdateKind.TRACKS_REPLACED
    )
    deck_draft: DeckDraft
    replacements: list[DeckDraftTrackReplacement]


class DeckDraftOperationStatus(BaseModel):
    operation: str
    success: bool
    reason: str | None = None


class DeckDraftToolResult(BaseModel):
    deck_draft: DeckDraft | None
    operations: list[DeckDraftOperationStatus]


type DeckDraftUpdate = (
    DeckDraftCreated
    | DeckDraftReplaced
    | DeckDraftTracksAdded
    | DeckDraftTracksRemoved
    | DeckDraftTracksReplaced
)
