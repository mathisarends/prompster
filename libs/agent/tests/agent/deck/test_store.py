import pytest
from agent.deck import (
    Deck,
    DeckCreatedEvent,
    DeckStore,
    DeckTrack,
    DeckTracksAddedEvent,
    DeckTracksRemovedEvent,
    TrackReplacement,
)


def _track(track_id: str, uri: str | None = None) -> DeckTrack:
    return DeckTrack(id=track_id, title=track_id, artist="Artist", spotify_uri=uri)


def test_first_add_creates_the_deck() -> None:
    store = DeckStore()

    change = store.add([_track("t1", "u:1")])

    assert isinstance(change, DeckCreatedEvent)
    assert change.deck == store.deck


def test_add_skips_known_uris_and_stops_at_capacity() -> None:
    store = DeckStore(
        Deck(id="d", name="Deck", tracks=(_track("t1", "u:1"),)), max_tracks=2
    )

    change = store.add([_track("t2", "u:1"), _track("t3", "u:3"), _track("t4", "u:4")])

    assert isinstance(change, DeckTracksAddedEvent)
    assert [track.id for track in change.tracks] == ["t3"]
    assert store.is_full


def test_add_without_new_tracks_changes_nothing() -> None:
    store = DeckStore(Deck(id="d", name="Deck", tracks=(_track("t1", "u:1"),)))

    assert store.add([_track("t2", "u:1")]) is None


def test_remove_and_replace_need_known_track_ids() -> None:
    store = DeckStore(Deck(id="d", name="Deck", tracks=(_track("t1"),)))

    with pytest.raises(ValueError, match="not found: t9"):
        store.remove(["t9"])
    with pytest.raises(ValueError, match="not found: t9"):
        store.replace([TrackReplacement(track_id="t9", track=_track("t2"))])


def test_edits_need_a_deck() -> None:
    with pytest.raises(ValueError, match="No Hitster deck"):
        DeckStore().remove(["t1"])


def test_replace_keeps_the_track_position() -> None:
    store = DeckStore(Deck(id="d", name="Deck", tracks=(_track("t1"), _track("t2"))))

    store.replace([TrackReplacement(track_id="t1", track=_track("t3"))])

    assert store.deck is not None
    assert [track.id for track in store.deck.tracks] == ["t3", "t2"]


def test_remove_duplicates_keeps_the_first_of_each_uri() -> None:
    tracks = (_track("t1", "u:1"), _track("t2", "u:1"), _track("t3"), _track("t4"))
    store = DeckStore(Deck(id="d", name="Deck", tracks=tracks))

    change = store.remove_duplicates()

    assert change == DeckTracksRemovedEvent(deck_id="d", track_ids=("t2",))
    assert store.remove_duplicates() is None
