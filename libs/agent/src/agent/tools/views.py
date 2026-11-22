from enum import StrEnum

from pydantic import BaseModel, Field


class ActionType(StrEnum):
    ASK_ONBOARDING_QUESTION = "ask_onboarding_question"
    SEARCH_TRACKS = "search_tracks"
    SEARCH_PLAYLISTS = "search_playlists"
    ADD_DECK_TRACKS = "add_deck_tracks"
    REMOVE_DECK_TRACKS = "remove_deck_tracks"
    REPLACE_DECK_TRACKS = "replace_deck_tracks"
    GET_SPOTIFY_PLAYLIST_TRACKS = "get_spotify_playlist_tracks"
    SELF_REVIEW = "self_review"


class OnboardingSelectionMode(StrEnum):
    SINGLE_SELECT = "single_select"
    MULTI_SELECT = "multi_select"


class InputRequest(BaseModel):
    question: str
    hint: str | None = None
    options: list[str] = Field(default_factory=list)
    recommended_option: str | None = None
    selection_mode: OnboardingSelectionMode = OnboardingSelectionMode.SINGLE_SELECT
    is_last_question: bool = False


class ActionResultItem(BaseModel):
    """A single result the agent surfaces from a tool execution.

    Bare preview metadata so a consumer can show the first results a tool
    produced — e.g. the tracks a search returned or the playlists it found.
    Track results also carry the artist and Spotify track URI; playlists leave
    those unset. Add fields only when a consumer actually needs them.
    """

    title: str
    cover_url: str | None = None
    artist: str | None = None
    track_uri: str | None = None


