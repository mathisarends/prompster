import base64
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from html import escape

from harnessed.models import ImagePart, TextPart, UserMessage


class UserCurationEventType(StrEnum):
    TRACK_ADDED = "track_added"
    TRACK_REMOVED = "track_removed"


@dataclass(frozen=True, slots=True)
class UserEvent:
    """A deck change the user made by hand, outside the agent's tools.

    It belongs to the user turn that follows it: the agent reads what the user
    changed since its last reply together with their next message.
    """

    type: UserCurationEventType
    occurred_at: datetime
    track_title: str | None = None
    track_artist: str | None = None

    @property
    def label(self) -> str:
        if self.track_artist and self.track_title:
            return f"{self.track_artist} - {self.track_title}"
        return self.track_artist or self.track_title or self.type.replace("_", " ")


@dataclass(frozen=True, slots=True)
class InputImage:
    media_type: str
    data: bytes

    @property
    def data_url(self) -> str:
        encoded = base64.b64encode(self.data).decode("ascii")
        return f"data:{self.media_type};base64,{encoded}"


def render_user_text(text: str, curation_events: Sequence[UserEvent] = ()) -> str:
    """The user's text, after a ``<user_events>`` block of their deck changes."""
    if not curation_events:
        return text
    lines = [
        "<user_events>",
        *(_render_event(event) for event in curation_events),
        "</user_events>",
    ]
    block = "\n".join(lines)
    return f"{block}\n\n{text}" if text else block


def user_input(
    text: str,
    *,
    images: Sequence[InputImage] = (),
    curation_events: Sequence[UserEvent] = (),
) -> UserMessage:
    rendered = render_user_text(text, curation_events)
    if not images:
        return UserMessage(rendered)
    parts = (
        TextPart(rendered or " "),
        *(ImagePart(image.data_url) for image in images),
    )
    return UserMessage(parts)


def _render_event(event: UserEvent) -> str:
    return (
        f'<event type="{escape(event.type.value, quote=True)}" '
        f'at="{escape(event.occurred_at.isoformat(), quote=True)}">'
        f"{escape(event.label)}</event>"
    )
