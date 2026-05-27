from uuid import UUID, uuid4

from .views import (
    PlaylistDraft,
    PlaylistDraftCreated,
    PlaylistDraftReplaced,
    PlaylistDraftTrack,
    PlaylistDraftTrackReplacement,
    PlaylistDraftTracksAdded,
    PlaylistDraftTracksRemoved,
    PlaylistDraftTracksReplaced,
    PlaylistDraftUpdate,
    TrackRef,
    TrackRefReplacement,
)


class PlaylistDraftStore:
    def __init__(self, playlist_draft: PlaylistDraft | None = None) -> None:
        self._playlist_draft = playlist_draft
        self._track_cache: dict[str, PlaylistDraftTrack] = {}
        self._pending_playlist_draft_updates: list[PlaylistDraftUpdate] = []

        if playlist_draft is not None:
            self.cache_tracks(playlist_draft.tracks)

    @property
    def playlist_draft(self) -> PlaylistDraft | None:
        return self._playlist_draft

    def save_playlist_draft(self, playlist_draft: PlaylistDraft) -> PlaylistDraft:
        self._assert_pinned_tracks_preserved(playlist_draft.tracks)
        update = (
            PlaylistDraftCreated(playlist_draft=playlist_draft)
            if self._playlist_draft is None
            else PlaylistDraftReplaced(playlist_draft=playlist_draft)
        )
        self._playlist_draft = playlist_draft
        self.cache_tracks(playlist_draft.tracks)
        self._pending_playlist_draft_updates.append(update)
        return playlist_draft

    def create_empty_playlist_draft(
        self,
        name: str,
    ) -> PlaylistDraft:
        if self._playlist_draft is not None:
            raise ValueError("Playlist draft already exists.")
        return self.save_playlist_draft(
            PlaylistDraft(
                name=name,
                tracks=[],
            )
        )

    def add_tracks(self, tracks: list[PlaylistDraftTrack]) -> PlaylistDraft:
        if self._playlist_draft is None:
            return self.save_playlist_draft(
                PlaylistDraft(name="Playlist", tracks=self._deduplicate_tracks(tracks))
            )

        playlist_draft = self._playlist_draft
        existing_uris = {track.spotify_uri for track in playlist_draft.tracks}
        tracks = self._deduplicate_tracks(tracks, existing_uris=existing_uris)
        if not tracks:
            return playlist_draft

        playlist_draft.tracks.extend(tracks)
        self.cache_tracks(tracks)
        self._pending_playlist_draft_updates.append(
            PlaylistDraftTracksAdded(
                playlist_draft=playlist_draft,
                tracks=tracks,
            )
        )
        return playlist_draft

    def add_track_refs(self, track_refs: list[TrackRef]) -> PlaylistDraft:
        return self.add_tracks(self.resolve_track_refs(track_refs))

    def remove_tracks(self, track_ids: list[UUID]) -> PlaylistDraft:
        playlist_draft = self._require_playlist_draft()
        track_id_set = set(track_ids)
        missing_track_ids = track_id_set - {track.id for track in playlist_draft.tracks}
        if missing_track_ids:
            missing = ", ".join(str(track_id) for track_id in sorted(missing_track_ids))
            raise ValueError(f"Playlist draft track(s) not found: {missing}")
        self._assert_no_pinned_track_ids(track_id_set)

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
        self._assert_no_pinned_track_ids(set(replacement_by_track_id))

        playlist_draft.tracks = [
            replacement_by_track_id[track.id].track
            if track.id in replacement_by_track_id
            else track
            for track in playlist_draft.tracks
        ]
        self.cache_tracks([replacement.track for replacement in replacements])
        self._pending_playlist_draft_updates.append(
            PlaylistDraftTracksReplaced(
                playlist_draft=playlist_draft,
                replacements=replacements,
            )
        )
        return playlist_draft

    def replace_track_refs(
        self,
        replacements: list[TrackRefReplacement],
    ) -> PlaylistDraft:
        resolved_replacements = [
            PlaylistDraftTrackReplacement(
                track_id=replacement.old_id,
                track=self.resolve_track_uri(replacement.new_uri),
            )
            for replacement in replacements
        ]
        return self.replace_tracks(resolved_replacements)

    def cache_tracks(self, tracks: list[PlaylistDraftTrack]) -> None:
        for track in tracks:
            if track.spotify_uri is not None:
                self._track_cache[track.spotify_uri] = track

    def resolve_track_refs(
        self, track_refs: list[TrackRef]
    ) -> list[PlaylistDraftTrack]:
        return [self.resolve_track_ref(track_ref) for track_ref in track_refs]

    def resolve_track_ref(self, track_ref: TrackRef) -> PlaylistDraftTrack:
        return self.resolve_track_uri(track_ref.uri)

    def resolve_track_uri(self, uri: str) -> PlaylistDraftTrack:
        track = self._track_cache.get(uri)
        if track is None:
            raise ValueError(f"Spotify track URI is not in the workspace cache: {uri}")
        return track.model_copy(update={"id": uuid4(), "is_pinned": False})

    def drain_playlist_draft_updates(self) -> list[PlaylistDraftUpdate]:
        updates = self._pending_playlist_draft_updates.copy()
        self._pending_playlist_draft_updates.clear()
        return updates

    def _require_playlist_draft(self) -> PlaylistDraft:
        if self._playlist_draft is None:
            raise ValueError("No playlist draft exists yet.")
        return self._playlist_draft

    def _deduplicate_tracks(
        self,
        tracks: list[PlaylistDraftTrack],
        *,
        existing_uris: set[str | None] | None = None,
    ) -> list[PlaylistDraftTrack]:
        seen_uris = set(existing_uris or set())
        deduplicated: list[PlaylistDraftTrack] = []
        for track in tracks:
            if track.spotify_uri in seen_uris:
                continue
            seen_uris.add(track.spotify_uri)
            deduplicated.append(track)
        return deduplicated

    def _assert_no_pinned_track_ids(self, track_ids: set[UUID]) -> None:
        playlist_draft = self._require_playlist_draft()
        pinned_track_ids = {
            track.id for track in playlist_draft.tracks if track.is_pinned
        } & track_ids
        if pinned_track_ids:
            pinned = ", ".join(str(track_id) for track_id in sorted(pinned_track_ids))
            raise ValueError(f"Playlist draft track(s) are pinned: {pinned}")

    def _assert_pinned_tracks_preserved(
        self,
        candidate_tracks: list[PlaylistDraftTrack],
    ) -> None:
        if self._playlist_draft is None:
            return

        candidate_by_id = {track.id: track for track in candidate_tracks}
        for existing_track in self._playlist_draft.tracks:
            if not existing_track.is_pinned:
                continue
            candidate = candidate_by_id.get(existing_track.id)
            if candidate is None or candidate != existing_track:
                raise ValueError(
                    f"Playlist draft track is pinned and cannot be changed: "
                    f"{existing_track.id}"
                )
