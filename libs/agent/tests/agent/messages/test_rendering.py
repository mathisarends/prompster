from datetime import UTC, datetime

from agent.deck import DeckDraft, DeckDraftTrack
from agent.messages import render_deck_state, render_user_message_content
from agent.views import UserCurationEventType, UserEvent

_REMOVED_BLOCK = (
    "<user_events>\n"
    '<event type="track_removed" at="2026-01-01T00:00:00+00:00">'
    "Rihanna - Umbrella</event>\n"
    "</user_events>"
)


def _event(
    *,
    type: UserCurationEventType = UserCurationEventType.TRACK_REMOVED,
    title: str | None = "Umbrella",
    artist: str | None = "Rihanna",
    at: datetime = datetime(2026, 1, 1, tzinfo=UTC),
) -> UserEvent:
    return UserEvent(type=type, track_title=title, track_artist=artist, occurred_at=at)


def test_text_without_events_passes_through() -> None:
    assert render_user_message_content("hi") == "hi"
    assert render_user_message_content("hi", None) == "hi"
    assert render_user_message_content("hi", []) == "hi"


def test_events_prepend_a_block_to_the_same_message() -> None:
    assert render_user_message_content("weiter", [_event()]) == (
        f"{_REMOVED_BLOCK}\n\nweiter"
    )


def test_events_without_text_render_only_the_block() -> None:
    assert render_user_message_content("", [_event()]) == _REMOVED_BLOCK


def test_multiple_events_share_one_block_in_input_order() -> None:
    first = _event(at=datetime(2026, 1, 1, 10, tzinfo=UTC))
    second = _event(
        type=UserCurationEventType.TRACK_ADDED,
        title="Take On Me",
        artist="a-ha",
        at=datetime(2026, 1, 1, 11, tzinfo=UTC),
    )

    assert render_user_message_content("weiter", [first, second]) == (
        "<user_events>\n"
        '<event type="track_removed" at="2026-01-01T10:00:00+00:00">'
        "Rihanna - Umbrella</event>\n"
        '<event type="track_added" at="2026-01-01T11:00:00+00:00">'
        "a-ha - Take On Me</event>\n"
        "</user_events>\n"
        "\n"
        "weiter"
    )


def test_event_labels_are_escaped() -> None:
    body = render_user_message_content(
        "ok",
        [_event(title='Song "X" & Y', artist="A&B")],
    )

    assert "A&amp;B - Song &quot;X&quot; &amp; Y" in body


def test_missing_deck_renders_an_empty_state() -> None:
    assert render_deck_state(None, max_tracks=50) == (
        '<deck_state track_count="0" max_tracks="50" />'
    )


def test_deck_state_lists_tracks_and_coverage() -> None:
    tracks = [
        DeckDraftTrack(
            title="Take On Me",
            artist="a-ha",
            year=1985,
            spotify_uri="spotify:track:1",
        ),
        DeckDraftTrack(
            title="Hunting High and Low",
            artist="a-ha, Morten Harket",
            year=None,
            spotify_uri="spotify:track:2",
        ),
    ]
    deck = DeckDraft(name="80er & mehr", tracks=tracks)

    state = render_deck_state(deck, max_tracks=50)

    assert (
        f'<deck_state id="{deck.id}" name="80er &amp; mehr" track_count="2" '
        'max_tracks="50" remaining_tracks="48">'
    ) in state
    assert (
        '<coverage decades="1980s: 1" undated="1" artists="1" top_artist="a-ha (2)" />'
    ) in state
    assert f'<track id="{tracks[0].id}" label="a-ha - Take On Me (1985)" />' in state
    assert state.endswith("</deck_state>")
