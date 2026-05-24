from enum import StrEnum
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


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
    is_locked: bool = Field(
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


type PlaylistDraftUpdate = (
    PlaylistDraftCreated
    | PlaylistDraftReplaced
    | PlaylistDraftTracksAdded
    | PlaylistDraftTracksRemoved
    | PlaylistDraftTracksReplaced
)


class WorkspaceStore:
    def __init__(self, playlist_draft: PlaylistDraft | None = None) -> None:
        self._playlist_draft = playlist_draft
        self._pending_playlist_draft_updates: list[PlaylistDraftUpdate] = []

    @property
    def playlist_draft(self) -> PlaylistDraft | None:
        return self._playlist_draft

    def save_playlist_draft(self, playlist_draft: PlaylistDraft) -> PlaylistDraft:
        self._assert_locked_tracks_preserved(playlist_draft.tracks)
        update = (
            PlaylistDraftCreated(playlist_draft=playlist_draft)
            if self._playlist_draft is None
            else PlaylistDraftReplaced(playlist_draft=playlist_draft)
        )
        self._playlist_draft = playlist_draft
        self._pending_playlist_draft_updates.append(update)
        return playlist_draft

    def add_tracks(self, tracks: list[PlaylistDraftTrack]) -> PlaylistDraft:
        playlist_draft = self._require_playlist_draft()
        playlist_draft.tracks.extend(tracks)
        self._pending_playlist_draft_updates.append(
            PlaylistDraftTracksAdded(
                playlist_draft=playlist_draft,
                tracks=tracks,
            )
        )
        return playlist_draft

    def remove_tracks(self, track_ids: list[UUID]) -> PlaylistDraft:
        playlist_draft = self._require_playlist_draft()
        track_id_set = set(track_ids)
        missing_track_ids = track_id_set - {track.id for track in playlist_draft.tracks}
        if missing_track_ids:
            missing = ", ".join(str(track_id) for track_id in sorted(missing_track_ids))
            raise ValueError(f"Playlist draft track(s) not found: {missing}")
        self._assert_no_locked_track_ids(track_id_set)

        playlist_draft.tracks = [
            track for track in playlist_draft.tracks if track.id not in track_id_set
        ]
        self._pending_playlist_draft_updates.append(
            PlaylistDraftTracksRemoved(
                playlist_draft=playlist_draft,
                track_ids=track_ids,
            )
        )
        return playlist_draft

    def replace_tracks(
        self,
        replacements: list[PlaylistDraftTrackReplacement],
    ) -> PlaylistDraft:
        playlist_draft = self._require_playlist_draft()
        replacement_by_track_id = {
            replacement.track_id: replacement for replacement in replacements
        }
        missing_track_ids = set(replacement_by_track_id) - {
            track.id for track in playlist_draft.tracks
        }
        if missing_track_ids:
            missing = ", ".join(str(track_id) for track_id in sorted(missing_track_ids))
            raise ValueError(f"Playlist draft track(s) not found: {missing}")
        self._assert_no_locked_track_ids(set(replacement_by_track_id))

        playlist_draft.tracks = [
            replacement_by_track_id[track.id].track
            if track.id in replacement_by_track_id
            else track
            for track in playlist_draft.tracks
        ]
        self._pending_playlist_draft_updates.append(
            PlaylistDraftTracksReplaced(
                playlist_draft=playlist_draft,
                replacements=replacements,
            )
        )
        return playlist_draft

    def drain_playlist_draft_updates(self) -> list[PlaylistDraftUpdate]:
        updates = self._pending_playlist_draft_updates.copy()
        self._pending_playlist_draft_updates.clear()
        return updates

    def _require_playlist_draft(self) -> PlaylistDraft:
        if self._playlist_draft is None:
            raise ValueError("No playlist draft exists yet.")
        return self._playlist_draft

    def _assert_no_locked_track_ids(self, track_ids: set[UUID]) -> None:
        playlist_draft = self._require_playlist_draft()
        locked_track_ids = {
            track.id for track in playlist_draft.tracks if track.is_locked
        } & track_ids
        if locked_track_ids:
            locked = ", ".join(str(track_id) for track_id in sorted(locked_track_ids))
            raise ValueError(f"Playlist draft track(s) are locked: {locked}")

    def _assert_locked_tracks_preserved(
        self,
        candidate_tracks: list[PlaylistDraftTrack],
    ) -> None:
        if self._playlist_draft is None:
            return

        candidate_by_id = {track.id: track for track in candidate_tracks}
        for existing_track in self._playlist_draft.tracks:
            if not existing_track.is_locked:
                continue
            candidate = candidate_by_id.get(existing_track.id)
            if candidate is None or not self._same_track(existing_track, candidate):
                raise ValueError(
                    f"Playlist draft track is locked and cannot be changed: "
                    f"{existing_track.id}"
                )

    def _same_track(
        self,
        left: PlaylistDraftTrack,
        right: PlaylistDraftTrack,
    ) -> bool:
        return (
            left.id == right.id
            and left.title == right.title
            and left.artist == right.artist
            and left.year == right.year
            and left.spotify_uri == right.spotify_uri
            and left.cover_url == right.cover_url
            and left.is_locked == right.is_locked
        )
