from collections.abc import Sequence
from enum import StrEnum

from harnessed.models import ToolCall
from harnessed.tools import ToolInfo, envelope_value
from pydantic import BaseModel, Field


class ActionType(StrEnum):
    SEARCH_TRACKS = "search_tracks"
    SEARCH_PLAYLISTS = "search_playlists"
    ADD_DECK_TRACKS = "add_deck_tracks"
    REMOVE_DECK_TRACKS = "remove_deck_tracks"
    REPLACE_DECK_TRACKS = "replace_deck_tracks"
    GET_SPOTIFY_PLAYLIST_TRACKS = "get_spotify_playlist_tracks"
    SELF_REVIEW = "self_review"


class StatusLabel(BaseModel):
    """UI status for tools whose label cannot be derived from their arguments."""

    status: str | None = Field(
        default=None,
        description="Short German present-tense UI label for this action.",
    )


class SequenceLabel(BaseModel):
    """UI label for a block of calls. It never reaches the tool."""

    sequence_label: str | None = Field(
        default=None,
        description=(
            "Short German label for a whole block of calls. "
            "Only on the first call of the block."
        ),
    )


def needs_status_label(tool: ToolInfo) -> bool:
    return tool.definition.name not in _DERIVED_STATUS_TOOLS


def action_type(tool_name: str) -> ActionType | None:
    return _ACTION_TYPES.get(tool_name)


def status_label(call: ToolCall) -> str | None:
    arguments = call.arguments
    match call.name:
        case "search_tracks":
            return _derived_label("Suche Tracks", arguments.get("query"))
        case "search_playlists":
            return _derived_label("Suche Playlists", arguments.get("query"))
        case "get_spotify_playlist_tracks":
            return _derived_label(
                "Hole Playlist-Tracks", arguments.get("playlist_name")
            )
    label = envelope_value(call, StatusLabel)
    return _clean(label.status) if label is not None else None


def batch_label(calls: Sequence[ToolCall]) -> str | None:
    """The label of a block of calls: its sequence label, else the first status."""
    for call in calls:
        label = envelope_value(call, SequenceLabel)
        if label is not None and (cleaned := _clean(label.sequence_label)):
            return cleaned
    for call in calls:
        if (status := status_label(call)) is not None:
            return status
    return None


_ACTION_TYPES = {
    "search_tracks": ActionType.SEARCH_TRACKS,
    "search_playlists": ActionType.SEARCH_PLAYLISTS,
    "add_deck_tracks": ActionType.ADD_DECK_TRACKS,
    "remove_deck_tracks": ActionType.REMOVE_DECK_TRACKS,
    "replace_deck_tracks": ActionType.REPLACE_DECK_TRACKS,
    "get_spotify_playlist_tracks": ActionType.GET_SPOTIFY_PLAYLIST_TRACKS,
    "review_deck": ActionType.SELF_REVIEW,
}
_DERIVED_STATUS_TOOLS = frozenset(
    {"search_tracks", "search_playlists", "get_spotify_playlist_tracks"}
)
_MAX_LABEL_LENGTH = 80
_MAX_VALUE_LENGTH = 32


def _derived_label(prefix: str, value: object) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    normalized = " ".join(value.split())
    if len(normalized) > _MAX_VALUE_LENGTH:
        normalized = f"{normalized[: _MAX_VALUE_LENGTH - 3].rstrip()}..."
    return f"{prefix}: {normalized}"


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    label = " ".join(value.split())
    if not label:
        return None
    if len(label) > _MAX_LABEL_LENGTH:
        return f"{label[: _MAX_LABEL_LENGTH - 3].rstrip()}..."
    return label
