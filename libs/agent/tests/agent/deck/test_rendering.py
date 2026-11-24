from agent.deck import Deck, DeckTrack
from agent.deck.rendering import render_deck_state


def test_missing_deck_renders_an_empty_state() -> None:
    assert render_deck_state(None, max_tracks=50) == (
        '<deck_state track_count="0" max_tracks="50" />'
    )


def test_deck_state_lists_tracks_and_coverage() -> None:
    tracks = (
        DeckTrack(id="t1", title="Take On Me", artist="a-ha", year=1985),
        DeckTrack(id="t2", title="Hunting High and Low", artist="a-ha, Morten Harket"),
    )
    deck = Deck(id="d1", name="80er & mehr", tracks=tracks)

    state = render_deck_state(deck, max_tracks=50)

    assert (
        '<deck_state id="d1" name="80er &amp; mehr" track_count="2" '
        'max_tracks="50" remaining_tracks="48">'
    ) in state
    assert (
        '<coverage decades="1980s: 1" undated="1" artists="1" top_artist="a-ha (2)" />'
    ) in state
    assert '<track id="t1" label="a-ha - Take On Me (1985)" />' in state
    assert state.endswith("</deck_state>")
