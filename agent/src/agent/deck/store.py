import logging
from uuid import UUID, uuid4

from .views import (
    DeckDraft,
    DeckDraftCreated,
    DeckDraftReplaced,
    DeckDraftTrack,
    DeckDraftTrackReplacement,
    DeckDraftTracksAdded,
    DeckDraftTracksRemoved,
    DeckDraftTracksReplaced,
    DeckDraftUpdate,
    TrackRef,
    TrackRefReplacement,
)

logger = logging.getLogger(__name__)


class DeckStore:
    def __init__(self, draft: DeckDraft | None = None) -> None:
        self._draft = draft
        self._track_cache: dict[str, DeckDraftTrack] = {}
        self._pending_updates: list[DeckDraftUpdate] = []

        if draft is not None:
            logger.info(
                "Initialized deck store with existing draft",
                extra={"deck_id": str(draft.id), "track_count": len(draft.tracks)},
            )
            self.cache_tracks(draft.tracks)

    @property
    def draft(self) -> DeckDraft | None:
        return self._draft

    def save_draft(self, draft: DeckDraft) -> DeckDraft:
        logger.info(
            "Saving deck draft",
            extra={
                "deck_id": str(draft.id),
                "track_count": len(draft.tracks),
                "is_new": self._draft is None,
            },
        )
        self._assert_pinned_tracks_preserved(draft.tracks)
        update = (
            DeckDraftCreated(deck_draft=draft)
            if self._draft is None
            else DeckDraftReplaced(deck_draft=draft)
        )
        self._draft = draft
        self.cache_tracks(draft.tracks)
        self._pending_updates.append(update)
        return draft

    def add_track_refs(self, track_refs: list[TrackRef]) -> DeckDraft:
        logger.info(
            "Adding track refs to deck",
            extra={
                "requested_track_refs": len(track_refs),
                "has_draft": self._draft is not None,
            },
        )
        return self.add_tracks(self.resolve_track_refs(track_refs))

    def add_tracks(self, tracks: list[DeckDraftTrack]) -> DeckDraft:
        logger.info(
            "Adding tracks to deck",
            extra={
                "requested_tracks": len(tracks),
                "has_draft": self._draft is not None,
            },
        )
        if self._draft is None:
            deduplicated_tracks = self._deduplicate_tracks(tracks)
            draft = DeckDraft(name="Deck", tracks=deduplicated_tracks)
            logger.info(
                "Created deck draft via add operation",
                extra={
                    "deck_id": str(draft.id),
                    "requested_tracks": len(tracks),
                    "added_tracks": len(deduplicated_tracks),
                    "skipped_duplicates": len(tracks) - len(deduplicated_tracks),
                },
            )
            return self.save_draft(draft)

        draft = self._draft
        existing_uris = {track.spotify_uri for track in draft.tracks}
        deduplicated_tracks = self._deduplicate_tracks(
            tracks, existing_uris=existing_uris
        )
        skipped_duplicates = len(tracks) - len(deduplicated_tracks)
        if not deduplicated_tracks:
            logger.info(
                "No new tracks added to deck",
                extra={
                    "deck_id": str(draft.id),
                    "requested_tracks": len(tracks),
                    "skipped_duplicates": skipped_duplicates,
                },
            )
            return draft

        draft.tracks.extend(deduplicated_tracks)
        self.cache_tracks(deduplicated_tracks)
        self._pending_updates.append(
            DeckDraftTracksAdded(
                deck_draft=draft,
                tracks=deduplicated_tracks,
            )
        )
        logger.info(
            "Added tracks to deck",
            extra={
                "deck_id": str(draft.id),
                "requested_tracks": len(tracks),
                "added_tracks": len(deduplicated_tracks),
                "skipped_duplicates": skipped_duplicates,
                "total_tracks": len(draft.tracks),
            },
        )
        return draft

    def remove_tracks(self, track_ids: list[UUID]) -> DeckDraft:
        logger.info(
            "Removing tracks from deck", extra={"requested_track_ids": len(track_ids)}
        )
        draft = self._require_draft()
        track_id_set = set(track_ids)
        missing_track_ids = track_id_set - {track.id for track in draft.tracks}
        if missing_track_ids:
            logger.warning(
                "Cannot remove missing deck tracks",
                extra={
                    "deck_id": str(draft.id),
                    "missing_track_ids": [
                        str(track_id) for track_id in missing_track_ids
                    ],
                },
            )
            missing = ", ".join(str(track_id) for track_id in sorted(missing_track_ids))
            raise ValueError(f"Hitster deck track(s) not found: {missing}")
        self._assert_no_pinned_track_ids(track_id_set)

        draft.tracks = [track for track in draft.tracks if track.id not in track_id_set]
        self._pending_updates.append(
            DeckDraftTracksRemoved(
                deck_draft=draft,
                track_ids=track_ids,
            )
        )
        logger.info(
            "Removed tracks from deck",
            extra={
                "deck_id": str(draft.id),
                "removed_tracks": len(track_ids),
                "total_tracks": len(draft.tracks),
            },
        )
        return draft

    def replace_tracks(
        self,
        replacements: list[DeckDraftTrackReplacement],
    ) -> DeckDraft:
        logger.info(
            "Replacing tracks in deck",
            extra={"requested_replacements": len(replacements)},
        )
        draft = self._require_draft()
        replacement_by_track_id = {
            replacement.track_id: replacement for replacement in replacements
        }
        missing_track_ids = set(replacement_by_track_id) - {
            track.id for track in draft.tracks
        }
        if missing_track_ids:
            logger.warning(
                "Cannot replace missing deck tracks",
                extra={
                    "deck_id": str(draft.id),
                    "missing_track_ids": [
                        str(track_id) for track_id in missing_track_ids
                    ],
                },
            )
            missing = ", ".join(str(track_id) for track_id in sorted(missing_track_ids))
            raise ValueError(f"Hitster deck track(s) not found: {missing}")
        self._assert_no_pinned_track_ids(set(replacement_by_track_id))

        draft.tracks = [
            replacement_by_track_id[track.id].track
            if track.id in replacement_by_track_id
            else track
            for track in draft.tracks
        ]
        self.cache_tracks([replacement.track for replacement in replacements])
        self._pending_updates.append(
            DeckDraftTracksReplaced(
                deck_draft=draft,
                replacements=replacements,
            )
        )
        logger.info(
            "Replaced tracks in deck",
            extra={
                "deck_id": str(draft.id),
                "replaced_tracks": len(replacements),
                "total_tracks": len(draft.tracks),
            },
        )
        return draft

    def replace_track_refs(
        self,
        replacements: list[TrackRefReplacement],
    ) -> DeckDraft:
        logger.info(
            "Resolving replacement track refs",
            extra={"requested_replacements": len(replacements)},
        )
        resolved_replacements = [
            DeckDraftTrackReplacement(
                track_id=replacement.old_id,
                track=self.resolve_track_uri(replacement.new_uri),
            )
            for replacement in replacements
        ]
        return self.replace_tracks(resolved_replacements)

    def cache_tracks(self, tracks: list[DeckDraftTrack]) -> None:
        cached_count = 0
        skipped_without_uri = 0
        for track in tracks:
            if track.spotify_uri is None:
                skipped_without_uri += 1
                continue
            self._track_cache[track.spotify_uri] = track
            cached_count += 1
        logger.info(
            "Cached deck candidate tracks",
            extra={
                "requested_tracks": len(tracks),
                "cached_tracks": cached_count,
                "skipped_without_uri": skipped_without_uri,
                "cache_size": len(self._track_cache),
            },
        )

    def resolve_track_refs(self, track_refs: list[TrackRef]) -> list[DeckDraftTrack]:
        return [self.resolve_track_ref(track_ref) for track_ref in track_refs]

    def resolve_track_ref(self, track_ref: TrackRef) -> DeckDraftTrack:
        return self.resolve_track_uri(track_ref.uri)

    def resolve_track_uri(self, uri: str) -> DeckDraftTrack:
        track = self._track_cache.get(uri)
        if track is None:
            logger.warning(
                "Track URI missing from deck cache", extra={"spotify_uri": uri}
            )
            raise ValueError(f"Spotify track URI is not in the workspace cache: {uri}")
        return track.model_copy(update={"id": uuid4(), "is_pinned": False})

    def drain_deck_draft_updates(self) -> list[DeckDraftUpdate]:
        updates = self._pending_updates.copy()
        self._pending_updates.clear()
        logger.info("Drained deck updates", extra={"update_count": len(updates)})
        return updates

    def _require_draft(self) -> DeckDraft:
        if self._draft is None:
            logger.warning("Deck operation failed because no draft exists")
            raise ValueError("No Hitster deck draft exists yet.")
        return self._draft

    def _deduplicate_tracks(
        self,
        tracks: list[DeckDraftTrack],
        *,
        existing_uris: set[str | None] | None = None,
    ) -> list[DeckDraftTrack]:
        seen_uris = set(existing_uris or set())
        deduplicated: list[DeckDraftTrack] = []
        for track in tracks:
            if track.spotify_uri in seen_uris:
                continue
            seen_uris.add(track.spotify_uri)
            deduplicated.append(track)
        return deduplicated

    def _assert_no_pinned_track_ids(self, track_ids: set[UUID]) -> None:
        draft = self._require_draft()
        pinned_track_ids = {
            track.id for track in draft.tracks if track.is_pinned
        } & track_ids
        if pinned_track_ids:
            logger.warning(
                "Deck operation attempted to change pinned tracks",
                extra={
                    "deck_id": str(draft.id),
                    "pinned_track_ids": [
                        str(track_id) for track_id in pinned_track_ids
                    ],
                },
            )
            pinned = ", ".join(str(track_id) for track_id in sorted(pinned_track_ids))
            raise ValueError(f"Hitster deck track(s) are pinned: {pinned}")

    def _assert_pinned_tracks_preserved(
        self,
        candidate_tracks: list[DeckDraftTrack],
    ) -> None:
        if self._draft is None:
            return

        candidate_by_id = {track.id: track for track in candidate_tracks}
        for existing_track in self._draft.tracks:
            if not existing_track.is_pinned:
                continue
            candidate = candidate_by_id.get(existing_track.id)
            if candidate is None or candidate != existing_track:
                logger.warning(
                    "Deck save attempted to change pinned track",
                    extra={
                        "deck_id": str(self._draft.id),
                        "track_id": str(existing_track.id),
                    },
                )
                raise ValueError(
                    f"Hitster deck track is pinned and cannot be changed: "
                    f"{existing_track.id}"
                )
