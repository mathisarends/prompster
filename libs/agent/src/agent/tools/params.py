from uuid import UUID

from pydantic import BaseModel, Field

from agent.deck import TrackRef, TrackRefReplacement
from agent.tools.views import OnboardingSelectionMode


class SearchParams(BaseModel):
    query: str = Field(description="Spotify search query.")
    limit: int = Field(default=10, ge=1, le=50, description="Maximum results.")


class ArtistAlbumsParams(BaseModel):
    artist_id: str = Field(description="URI or ID.")
    include_groups: str = Field(default="album,single", description="Comma-separated.")
    limit: int = 20


class ArtistTopTracksParams(BaseModel):
    artist_id: str = Field(description="URI or ID.")
    country: str = Field(default="DE", description="ISO 3166-1 alpha-2.")


class AlbumTracksParams(BaseModel):
    album_id: str = Field(description="URI or ID.")


class AddDraftDeckTracksParams(BaseModel):
    tracks: list[TrackRef] = Field(
        min_length=1,
        description="Spotify track URIs from search or playlist results.",
    )


class RemoveDraftDeckTracksParams(BaseModel):
    track_ids: list[UUID] = Field(
        min_length=1,
        description="Track IDs from the current deck state.",
    )


class ReplaceDraftDeckTracksParams(BaseModel):
    replacements: list[TrackRefReplacement] = Field(
        min_length=1,
        description="Deck track IDs to swap for Spotify track URIs.",
    )


class PlaylistIdParams(BaseModel):
    playlist_id: str = Field(description="Spotify playlist URI or ID.")
    playlist_name: str = Field(
        description=(
            "Readable playlist name from the search result, shown in the UI. "
            "Never the playlist ID."
        ),
    )
    offset: int = Field(
        default=0,
        ge=0,
        description="Zero-based page offset. Start at 0.",
    )


class AskOnboardingQuestionParams(BaseModel):
    question: str = Field(description="The question shown to the user.")
    hint: str | None = Field(
        default=None,
        description="Optional short note below the question: a tip or a warning.",
    )
    selection_mode: OnboardingSelectionMode = Field(
        default=OnboardingSelectionMode.SINGLE_SELECT,
        description="single_select for one answer, multi_select for several.",
    )
    options: list[str] = Field(
        min_length=2,
        max_length=4,
        description="2-4 tag-style answers of about three words each.",
    )
    recommended_option: str | None = Field(
        default=None,
        description="Your recommendation, copied verbatim from options.",
    )
    is_last_question: bool = Field(
        default=False,
        description="True only on the final question of this onboarding.",
    )
