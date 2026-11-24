from dataclasses import dataclass, field
from enum import StrEnum
from typing import Literal

from harnessed.events import TransientEvent

from agent.deck.views import Deck, DeckTrack, TrackReplacement


class DeckEventKind(StrEnum):
    CREATED = "deck.created"
    TRACKS_ADDED = "deck.tracks.added"
    TRACKS_REMOVED = "deck.tracks.removed"
    TRACKS_REPLACED = "deck.tracks.replaced"


@dataclass(frozen=True, slots=True)
class DeckCreatedEvent(TransientEvent):
    deck: Deck
    type: Literal[DeckEventKind.CREATED] = field(
        default=DeckEventKind.CREATED, kw_only=True
    )


@dataclass(frozen=True, slots=True)
class DeckTracksAddedEvent(TransientEvent):
    deck_id: str
    tracks: tuple[DeckTrack, ...]
    type: Literal[DeckEventKind.TRACKS_ADDED] = field(
        default=DeckEventKind.TRACKS_ADDED, kw_only=True
    )


@dataclass(frozen=True, slots=True)
class DeckTracksRemovedEvent(TransientEvent):
    deck_id: str
    track_ids: tuple[str, ...]
    type: Literal[DeckEventKind.TRACKS_REMOVED] = field(
        default=DeckEventKind.TRACKS_REMOVED, kw_only=True
    )


@dataclass(frozen=True, slots=True)
class DeckTracksReplacedEvent(TransientEvent):
    deck_id: str
    replacements: tuple[TrackReplacement, ...]
    type: Literal[DeckEventKind.TRACKS_REPLACED] = field(
        default=DeckEventKind.TRACKS_REPLACED, kw_only=True
    )


type DeckChangedEvent = (
    DeckCreatedEvent
    | DeckTracksAddedEvent
    | DeckTracksRemovedEvent
    | DeckTracksReplacedEvent
)

DECK_EVENTS = (
    DeckCreatedEvent,
    DeckTracksAddedEvent,
    DeckTracksRemovedEvent,
    DeckTracksReplacedEvent,
)
