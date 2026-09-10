from collections.abc import Sequence
from html import escape

from agent.views import UserEvent
from agent.deck import DeckDraft
from agent.deck.views import DeckDraftTrack


def render_user_message_content(
    content: str,
    curation_events: Sequence[UserEvent] | None = None,
) -> str:
    """Compose a user message body, prepending a ``<user_events>`` block when given."""
    if not curation_events:
        return content
    block = _render_user_events_block(curation_events)
    if not content:
        return block
    return f"{block}\n\n{content}"


def _render_user_events_block(events: Sequence[UserEvent]) -> str:
    """Render UserEvents as a single ``<user_events>`` XML block.

    The block is meant to be embedded inside the same ``UserMessage`` content
    as the user's text - it represents manual Hitster deck changes the user made
    just before that turn.
    """
    lines = ["<user_events>"]
    lines.extend(_render_event(event) for event in events)
    lines.append("</user_events>")
    return "\n".join(lines)


def _render_event(event: UserEvent) -> str:
    return (
        f'<event type="{escape(event.type.value, quote=True)}" '
        f'at="{escape(event.occurred_at.isoformat(), quote=True)}">'
        f"{escape(event.label)}</event>"
    )


def render_deck_context(
    deck_draft: DeckDraft,
    *,
    max_tracks: int,
) -> str:
    track_count = len(deck_draft.tracks)
    remaining_tracks = max(0, max_tracks - track_count)
    lines = [
        (
            f'<created_deck id="{deck_draft.id}" '
            f'name="{escape(deck_draft.name, quote=True)}" '
            f'track_count="{track_count}" '
            f'max_tracks="{max_tracks}" '
            f'remaining_tracks="{remaining_tracks}">'
        ),
    ]
    lines.extend(render_track_tag(track) for track in deck_draft.tracks)
    lines.append("</created_deck>")
    return "\n".join(lines)


def render_track_tag(
    track: DeckDraftTrack,
    *,
    identity_attr: str = "id",
    identity_value: str | None = None,
) -> str:
    attrs = [
        (identity_attr, identity_value or str(track.id)),
        ("label", _render_track_label(track)),
    ]
    return f"<track {_render_attrs(attrs)} />"


def render_album_tag(
    *,
    uri: str | None,
    name: str,
    artist: str,
    year: int | None,
    track_count: int | None,
) -> str:
    attrs = [
        ("uri", uri),
        ("label", _render_release_label(artist, name, year)),
        ("tracks", str(track_count) if track_count is not None else None),
    ]
    return f"<album {_render_attrs(attrs)} />"


def render_playlist_tag(
    *,
    id: str | None,
    name: str,
    track_count: int | None,
) -> str:
    attrs = [
        ("id", id),
        ("label", name),
        ("tracks", str(track_count) if track_count is not None else None),
    ]
    return f"<playlist {_render_attrs(attrs)} />"


def _render_track_label(track: DeckDraftTrack) -> str:
    return _render_release_label(track.artist, track.title, track.year)


def _render_release_label(artist: str, title: str, year: int | None) -> str:
    label = f"{artist} - {title}"
    if year:
        label = f"{label} ({year})"
    return label


def _render_attrs(attrs: list[tuple[str, str | None]]) -> str:
    return " ".join(
        f'{name}="{escape(value, quote=True)}"'
        for name, value in attrs
        if value is not None and value != ""
    )
