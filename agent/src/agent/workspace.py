from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


class PlaylistDraftTrack(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    title: str = Field(description="Track title.")
    artist: str = Field(description="Primary artist or comma-separated artists.")
    year: int | None = Field(default=None, description="Release year.")
    spotify_uri: str = Field(description="Spotify track URI, e.g. spotify:track:...")
    cover_url: str | None = Field(default=None, description="Album cover image URL.")

    @field_validator("spotify_uri")
    @classmethod
    def require_track_uri(cls, value: str) -> str:
        if not value.startswith("spotify:track:"):
            raise ValueError("spotify_uri must start with 'spotify:track:'")
        return value


class PlaylistDraft(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    tracks: list[PlaylistDraftTrack]


class WorkspaceStore:
    def __init__(self) -> None:
        self._playlist_draft: PlaylistDraft | None = None
        self._pending_playlist_draft_updates: list[PlaylistDraft] = []

    @property
    def playlist_draft(self) -> PlaylistDraft | None:
        return self._playlist_draft

    def save_playlist_draft(self, playlist_draft: PlaylistDraft) -> PlaylistDraft:
        self._playlist_draft = playlist_draft
        self._pending_playlist_draft_updates.append(playlist_draft)
        return playlist_draft

    def drain_playlist_draft_updates(self) -> list[PlaylistDraft]:
        updates = self._pending_playlist_draft_updates.copy()
        self._pending_playlist_draft_updates.clear()
        return updates
