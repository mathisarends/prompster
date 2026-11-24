from datetime import UTC, datetime

from agent.conversation import (
    InputImage,
    UserCurationEventType,
    UserEvent,
    render_user_text,
    user_input,
)
from harnessed.models import ImagePart, TextPart

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
    assert render_user_text("hi") == "hi"


def test_events_prepend_a_block_to_the_same_message() -> None:
    assert render_user_text("weiter", [_event()]) == f"{_REMOVED_BLOCK}\n\nweiter"


def test_events_without_text_render_only_the_block() -> None:
    assert render_user_text("", [_event()]) == _REMOVED_BLOCK


def test_multiple_events_share_one_block_in_input_order() -> None:
    first = _event(at=datetime(2026, 1, 1, 10, tzinfo=UTC))
    second = _event(
        type=UserCurationEventType.TRACK_ADDED,
        title="Take On Me",
        artist="a-ha",
        at=datetime(2026, 1, 1, 11, tzinfo=UTC),
    )

    assert render_user_text("weiter", [first, second]) == (
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
    body = render_user_text("ok", [_event(title='Song "X" & Y', artist="A&B")])

    assert "A&amp;B - Song &quot;X&quot; &amp; Y" in body


def test_images_follow_the_text_as_data_urls() -> None:
    message = user_input("Schau", images=[InputImage("image/png", b"png")])

    assert message.content == (
        TextPart("Schau"),
        ImagePart("data:image/png;base64,cG5n"),
    )
