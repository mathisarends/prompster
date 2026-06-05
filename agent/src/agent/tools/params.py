from uuid import UUID

from pydantic import BaseModel, Field

from agent.playlist.views import TrackRef, TrackRefReplacement
from agent.tools.views import OnboardingSelectionMode


class ToolParams(BaseModel):
    status: str = Field(
        description=(
            "Kurzes deutsches Status-Label im Präsens (max. ~50 Zeichen), das dem "
            "Nutzer anzeigt, was du gerade tust. Beispiele: \"Suche nach 'Abba'\", "
            '"Album-Tracks laden", "Playlist-Entwurf bauen: \'80er Party\'".'
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


class CreateDraftPlaylistParams(ToolParams):
    name: str


class AddDraftPlaylistTracksParams(ToolParams):
    tracks: list[TrackRef] = Field(min_length=1)


class RemoveDraftPlaylistTracksParams(ToolParams):
    track_ids: list[UUID] = Field(min_length=1)


class ReplaceDraftPlaylistTracksParams(ToolParams):
    replacements: list[TrackRefReplacement] = Field(min_length=1)


class PlaylistIdParams(ToolParams):
    playlist_id: str


class AskOnboardingQuestionParams(ToolParams):
    status: str = "Stelle Onboarding-Frage..."
    question: str
    selection_mode: OnboardingSelectionMode = Field(
        default=OnboardingSelectionMode.SINGLE_SELECT,
        description=(
            "Use single_select when exactly one answer should be chosen. "
            "Use multi_select when the user may choose one or more answers."
        ),
    )
    options: list[str] = Field(
        min_length=3,
        max_length=8,
        description="3-8 concise, meaningful suggested answers for the user.",
    )
    is_last_question: bool = False
