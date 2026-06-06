from dataclasses import dataclass
from enum import StrEnum


class ToolActionType(StrEnum):
    ASK_ONBOARDING_QUESTION = "ask_onboarding_question"
    SEARCH_TRACKS = "search_tracks"
    SEARCH_PLAYLISTS = "search_playlists"
    ADD_DECK_TRACKS = "add_deck_tracks"
    REMOVE_DECK_TRACKS = "remove_deck_tracks"
    REPLACE_DECK_TRACKS = "replace_deck_tracks"
    GET_SPOTIFY_PLAYLIST_TRACKS = "get_spotify_playlist_tracks"
    SELF_REVIEW = "self_review"


@dataclass(frozen=True)
class ToolFunction:
    name: str
    arguments: dict[str, object]
    status_label: str | None = None
    action_type: ToolActionType | None = None
    is_onboarding_question: bool = False


@dataclass(frozen=True)
class PendingCall:
    id: str
    function: ToolFunction


@dataclass(frozen=True)
class CompletedCall:
    id: str
    function: ToolFunction
    result: str


@dataclass(frozen=True)
class FailedCall:
    id: str
    function: ToolFunction
    error: str


type ResolvedCall = CompletedCall | FailedCall
type ToolCall = PendingCall | ResolvedCall


def is_pending(call: ToolCall) -> bool:
    return isinstance(call, PendingCall)


def is_resolved(call: ToolCall) -> bool:
    return not is_pending(call)
