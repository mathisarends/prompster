from uuid import UUID

from pydantic import BaseModel, Field

from agent.deck.views import TrackRef, TrackRefReplacement
from agent.tools.views import OnboardingSelectionMode


class ToolParams(BaseModel):
    status: str = Field(
        description=(
            "Kurzes deutsches Status-Label im Präsens (max. ~50 Zeichen), das dem "
            "Nutzer anzeigt, was du gerade tust. Beispiele: \"Suche nach 'Abba'\", "
            '"Spotify-Playlist durchstoebern", "Hitster-Deck bauen: \'80er Party\'".'
        ),
    )


class SearchParams(ToolParams):
    query: str
    limit: int = 10


class ArtistAlbumsParams(ToolParams):
    artist_id: str = Field(description="URI or ID.")
    include_groups: str = Field(default="album,single", description="Comma-separated.")
    limit: int = 20


class ArtistTopTracksParams(ToolParams):
    artist_id: str = Field(description="URI or ID.")
    country: str = Field(default="DE", description="ISO 3166-1 alpha-2.")


class AlbumTracksParams(ToolParams):
    album_id: str = Field(description="URI or ID.")


class AddDraftDeckTracksParams(ToolParams):
    tracks: list[TrackRef] = Field(min_length=1)


class RemoveDraftDeckTracksParams(ToolParams):
    track_ids: list[UUID] = Field(min_length=1)


class ReplaceDraftDeckTracksParams(ToolParams):
    replacements: list[TrackRefReplacement] = Field(min_length=1)


class PlaylistIdParams(ToolParams):
    playlist_id: str


class AskOnboardingQuestionParams(ToolParams):
    status: str = "Stelle Onboarding-Frage..."
    question: str
    hint: str | None = Field(
        default=None,
        description=(
            "Optional short note shown below the question in the UI. "
            "Use for warnings, tips, or contextual info the user should see "
            "before answering."
        ),
    )
    selection_mode: OnboardingSelectionMode = Field(
        default=OnboardingSelectionMode.SINGLE_SELECT,
        description=(
            "Use single_select when exactly one answer should be chosen. "
            "Use multi_select when the user may choose one or more answers."
        ),
    )
    options: list[str] = Field(
        min_length=3,
        max_length=6,
        description="3-6 concise, meaningful suggested answers for the user.",
    )
    is_last_question: bool = False
