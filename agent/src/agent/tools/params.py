from uuid import UUID

from pydantic import BaseModel, Field

from agent.deck.views import TrackRef, TrackRefReplacement
from agent.tools.views import OnboardingSelectionMode


def _compact_status_value(value: str, max_length: int = 32) -> str:
    normalized_value = " ".join(value.split())
    if len(normalized_value) > max_length:
        return f"{normalized_value[: max_length - 3].rstrip()}..."
    return normalized_value


class SequenceLabelParams(BaseModel):
    sequence_label: str | None = Field(
        default=None,
        max_length=80,
        description=(
            "Optionales kurzes deutsches Label fuer den gesamten Tool-Block. "
            "Nur im ersten Tool Call setzen, wenn mehrere Tool Calls zu einem "
            "gemeinsamen Arbeitsschritt gehoeren."
        ),
    )


class ToolParams(SequenceLabelParams):
    status: str = Field(
        description=(
            "Kurzes deutsches Status-Label im Präsens (max. ~50 Zeichen), das dem "
            "Nutzer anzeigt, was du gerade tust. Beispiele: \"Suche nach 'Abba'\", "
            '"Spotify-Playlist durchstoebern", "Hitster-Deck bauen: \'80er Party\'".'
        ),
    )


class SearchParams(SequenceLabelParams):
    query: str
    limit: int = 10

    def status_label(self, kind: str) -> str:
        return f"Suche {kind}: {_compact_status_value(self.query)}"


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


class PlaylistIdParams(SequenceLabelParams):
    playlist_id: str = Field(description="Spotify playlist URI or ID.")
    playlist_name: str = Field(
        description=(
            "Human-readable playlist name from the selected Spotify search result. "
            "Used only for the visible tool status. Do not put the playlist ID here."
        ),
    )

    def status_label(self) -> str:
        return f"Hole Playlist-Tracks: {_compact_status_value(self.playlist_name)}"


class ReviewDeckParams(ToolParams):
    status: str = "Prüfe das Deck auf Balance..."


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
        min_length=2,
        max_length=4,
        description=(
            "2-4 ultra-short tag-style answers (aim for 3). Max ~3 words each, "
            "no full sentences. E.g. 'Alle Jahrzehnte', not 'So breit wie "
            "moeglich ueber mehrere Jahrzehnte'."
        ),
    )
    recommended_option: str | None = Field(
        default=None,
        description=(
            "Exactly one of the option strings, marked as your recommendation. "
            "Must match one entry in options verbatim. Always provide one."
        ),
    )
    is_last_question: bool = False
