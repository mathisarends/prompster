from enum import StrEnum
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


class TrackRef(BaseModel):
    uri: str = Field(description="Spotify track URI, e.g. spotify:track:...")
    pinned: bool = Field(
        default=False,
        description="Whether this track should be pinned in the playlist draft.",
    )

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


class PlaylistDraftTrack(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    title: str = Field(description="Track title.")
    artist: str = Field(description="Primary artist or comma-separated artists.")
    year: int | None = Field(default=None, description="Release year.")
    spotify_uri: str | None = Field(
        default=None,
        description="Spotify track URI, e.g. spotify:track:...",
    )
    cover_url: str | None = Field(default=None, description="Album cover image URL.")
    is_pinned: bool = Field(
        default=False,
        description="Whether this track is pinned and must not be removed or replaced.",
    )

    @field_validator("spotify_uri")
    @classmethod
    def require_track_uri(cls, value: str | None) -> str | None:
        if value is not None and not value.startswith("spotify:track:"):
            raise ValueError("spotify_uri must start with 'spotify:track:'")
        return value


class PlaylistDraft(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    tracks: list[PlaylistDraftTrack]


class PlaylistDraftUpdateKind(StrEnum):
    CREATED = "created"
    REPLACED = "replaced"
    TRACKS_ADDED = "tracks_added"
    TRACKS_REMOVED = "tracks_removed"
    TRACKS_REPLACED = "tracks_replaced"


class PlaylistDraftCreated(BaseModel):
    kind: Literal[PlaylistDraftUpdateKind.CREATED] = PlaylistDraftUpdateKind.CREATED
    playlist_draft: PlaylistDraft


class PlaylistDraftReplaced(BaseModel):
    kind: Literal[PlaylistDraftUpdateKind.REPLACED] = PlaylistDraftUpdateKind.REPLACED
    playlist_draft: PlaylistDraft


class PlaylistDraftTracksAdded(BaseModel):
    kind: Literal[PlaylistDraftUpdateKind.TRACKS_ADDED] = (
        PlaylistDraftUpdateKind.TRACKS_ADDED
    )
    playlist_draft: PlaylistDraft
    tracks: list[PlaylistDraftTrack]


class PlaylistDraftTracksRemoved(BaseModel):
    kind: Literal[PlaylistDraftUpdateKind.TRACKS_REMOVED] = (
        PlaylistDraftUpdateKind.TRACKS_REMOVED
    )
    playlist_draft: PlaylistDraft
    track_ids: list[UUID]


class PlaylistDraftTrackReplacement(BaseModel):
    track_id: UUID
    track: PlaylistDraftTrack


class PlaylistDraftTracksReplaced(BaseModel):
    kind: Literal[PlaylistDraftUpdateKind.TRACKS_REPLACED] = (
        PlaylistDraftUpdateKind.TRACKS_REPLACED
    )
    playlist_draft: PlaylistDraft
    replacements: list[PlaylistDraftTrackReplacement]


class PlaylistDraftOperationStatus(BaseModel):
    operation: str
    success: bool
    reason: str | None = None


class PlaylistDraftToolResult(BaseModel):
    playlist_draft: PlaylistDraft | None
    operations: list[PlaylistDraftOperationStatus]


type PlaylistDraftUpdate = (
    PlaylistDraftCreated
    | PlaylistDraftReplaced
    | PlaylistDraftTracksAdded
    | PlaylistDraftTracksRemoved
    | PlaylistDraftTracksReplaced
)
