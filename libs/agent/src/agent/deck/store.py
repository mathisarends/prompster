import logging
from collections.abc import Sequence
from dataclasses import replace
from uuid import uuid4

from agent.deck.events import (
    DeckChangedEvent,
    DeckCreatedEvent,
    DeckTracksAddedEvent,
    DeckTracksRemovedEvent,
    DeckTracksReplacedEvent,
)
from agent.deck.views import Deck, DeckTrack, TrackReplacement

logger = logging.getLogger(__name__)


class DeckStore:
    """The deck of one run. Every change returns the event that describes it."""

    def __init__(self, deck: Deck | None = None, *, max_tracks: int = 50) -> None:
        self._deck = deck
        self.max_tracks = max_tracks

    @property
    def deck(self) -> Deck | None:
        return self._deck

    @property
    def track_count(self) -> int:
        return len(self._deck.tracks) if self._deck is not None else 0

    @property
    def is_full(self) -> bool:
        return self.track_count >= self.max_tracks

    def add(self, tracks: Sequence[DeckTrack]) -> DeckChangedEvent | None:
        """Add tracks that are not in the deck yet, up to its capacity."""
        current = self._deck.tracks if self._deck is not None else ()
        known_uris = {track.spotify_uri for track in current}
        fresh: list[DeckTrack] = []
        for track in tracks:
            if track.spotify_uri in known_uris:
                continue
            known_uris.add(track.spotify_uri)
            fresh.append(track)
        added = tuple(fresh[: max(0, self.max_tracks - len(current))])
        logger.info(
            "Adding tracks to deck",
            extra={"requested": len(tracks), "added": len(added)},
        )
        if self._deck is None:
            self._deck = Deck(id=str(uuid4()), name="Deck", tracks=added)
            return DeckCreatedEvent(deck=self._deck)
        if not added:
            return None
        self._deck = replace(self._deck, tracks=(*current, *added))
        return DeckTracksAddedEvent(deck_id=self._deck.id, tracks=added)

    def remove(self, track_ids: Sequence[str]) -> DeckTracksRemovedEvent:
        deck = self._require_deck()
        self._require_tracks(deck, track_ids)
        removed = set(track_ids)
        self._deck = replace(
            deck,
            tracks=tuple(track for track in deck.tracks if track.id not in removed),
        )
        return DeckTracksRemovedEvent(deck_id=deck.id, track_ids=tuple(track_ids))

    def replace(
        self, replacements: Sequence[TrackReplacement]
    ) -> DeckTracksReplacedEvent:
        deck = self._require_deck()
        by_id = {
            replacement.track_id: replacement.track for replacement in replacements
        }
        self._require_tracks(deck, list(by_id))
        self._deck = replace(
            deck, tracks=tuple(by_id.get(track.id, track) for track in deck.tracks)
        )
        return DeckTracksReplacedEvent(
            deck_id=deck.id, replacements=tuple(replacements)
        )

    def remove_duplicates(self) -> DeckTracksRemovedEvent | None:
        """Drop tracks that repeat a Spotify URI, keeping the first of each."""
        if self._deck is None:
            return None
        seen: set[str] = set()
        duplicates: list[str] = []
        for track in self._deck.tracks:
            if track.spotify_uri is None:
                continue
            if track.spotify_uri in seen:
                duplicates.append(track.id)
            seen.add(track.spotify_uri)
        return self.remove(duplicates) if duplicates else None

    def _require_deck(self) -> Deck:
        if self._deck is None:
            raise ValueError("No Hitster deck draft exists yet.")
        return self._deck

    def _require_tracks(self, deck: Deck, track_ids: Sequence[str]) -> None:
        missing = set(track_ids) - {track.id for track in deck.tracks}
        if missing:
            raise ValueError(
                f"Hitster deck track(s) not found: {', '.join(sorted(missing))}"
            )
