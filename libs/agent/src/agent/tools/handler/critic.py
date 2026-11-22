import logging
from collections import Counter

from callm import ChatModel, SystemMessage, UserMessage
from pydantic import BaseModel, Field

from agent.deck import DeckDraftTrack, DeckStore
from agent.messages import MessageManager

logger = logging.getLogger(__name__)

# Below this many tracks a coverage review is not meaningful yet.
_MIN_TRACKS_FOR_REVIEW = 6


class DeckReviewMetrics(BaseModel):
    track_count: int
    target_size: int
    distinct_artists: int
    distinct_decades: int
    distinct_years: int
    tracks_without_year: int
    top_artist: str | None
    top_artist_count: int
    top_artist_share: float
    top_decade: int | None
    top_decade_count: int
    top_decade_share: float
    artist_diversity: float


class DeckCritiqueSuggestion(BaseModel):
    issue: str = Field(description="What is wrong, naming the artist or era.")
    action: str = Field(
        description=(
            "A concrete refinement the deck builder can apply directly, e.g. "
            "remove/replace a specific over-represented track or add coverage "
            "for a missing decade."
        )
    )


class DeckCritique(BaseModel):
    assessment: str = Field(description="One or two sentence overall verdict.")
    needs_refinement: bool = Field(
        description="True only if the deck genuinely benefits from another pass."
    )
    suggestions: list[DeckCritiqueSuggestion] = Field(default_factory=list)


class DeckReviewResult(BaseModel):
    content: str
    triggered_llm: bool
    metrics: DeckReviewMetrics | None = None


class DeckCritic:
    """Reviews the current Hitster deck for artist and era concentration.

    Mirrors the ``Spotify`` handler shape: it performs deterministic static
    checks first and only escalates to an injected LLM for structured,
    directly-actionable feedback when the deck is noticeably skewed toward one
    artist or one time period relative to the target deck size.
    """

    def __init__(
        self,
        llm: ChatModel,
        *,
        deck_store: DeckStore,
        message_manager: MessageManager,
        target_size: int = 50,
    ) -> None:
        self._llm = llm
        self._deck_store = deck_store
        self._message_manager = message_manager
        self._target_size = target_size

    async def review(self) -> DeckReviewResult:
        draft = self._deck_store.draft
        if draft is None or not draft.tracks:
            return DeckReviewResult(
                content="No deck draft exists yet; nothing to review.",
                triggered_llm=False,
            )

        track_count = len(draft.tracks)
        if track_count < _MIN_TRACKS_FOR_REVIEW:
            return DeckReviewResult(
                content=(
                    f"Deck has only {track_count} track(s); too small for a "
                    "coverage review. Keep building first."
                ),
                triggered_llm=False,
            )

        metrics = self._compute_metrics(draft.tracks, self._target_size)
        concerns = self._detect_concerns(metrics)

        logger.info(
            "Deck review computed",
            extra={
                "track_count": metrics.track_count,
                "target_size": metrics.target_size,
                "distinct_artists": metrics.distinct_artists,
                "distinct_decades": metrics.distinct_decades,
                "concern_count": len(concerns),
            },
        )

        brief = self._message_manager.conversation_transcript()
        critique = await self._request_critique(draft.tracks, metrics, concerns, brief)
        return DeckReviewResult(
            content=self._render_critique(metrics, concerns, critique),
            triggered_llm=True,
            metrics=metrics,
        )

    def _compute_metrics(
        self,
        tracks: list[DeckDraftTrack],
        target: int,
    ) -> DeckReviewMetrics:
        track_count = len(tracks)
        artist_counts = Counter(_primary_artist(track.artist) for track in tracks)
        years = [track.year for track in tracks if track.year]
        decade_counts = Counter((year // 10) * 10 for year in years)

        top_artist, top_artist_count = (
            artist_counts.most_common(1)[0] if artist_counts else (None, 0)
        )
        top_decade, top_decade_count = (
            decade_counts.most_common(1)[0] if decade_counts else (None, 0)
        )

        return DeckReviewMetrics(
            track_count=track_count,
            target_size=target,
            distinct_artists=len(artist_counts),
            distinct_decades=len(decade_counts),
            distinct_years=len(set(years)),
            tracks_without_year=track_count - len(years),
            top_artist=top_artist,
            top_artist_count=top_artist_count,
            top_artist_share=top_artist_count / track_count if track_count else 0.0,
            top_decade=top_decade,
            top_decade_count=top_decade_count,
            top_decade_share=top_decade_count / len(years) if years else 0.0,
            artist_diversity=len(artist_counts) / track_count if track_count else 0.0,
        )

    def _detect_concerns(self, metrics: DeckReviewMetrics) -> list[str]:
        """Static gate. Only concentration relative to deck size should fire."""
        concerns: list[str] = []
        track_count = metrics.track_count
        max_per_artist = max(2, round(metrics.target_size * 0.12))

        if (
            metrics.top_artist is not None
            and metrics.top_artist_count > max_per_artist
            and metrics.top_artist_share >= 0.18
        ):
            concerns.append(
                f"Artist '{metrics.top_artist}' appears "
                f"{metrics.top_artist_count}x ({metrics.top_artist_share:.0%} of "
                f"the deck); expected at most ~{max_per_artist} for a "
                f"{metrics.target_size}-track deck."
            )

        if metrics.distinct_years:
            if metrics.top_decade is not None and metrics.top_decade_share >= 0.5:
                concerns.append(
                    f"The {metrics.top_decade}s make up "
                    f"{metrics.top_decade_share:.0%} of dated tracks; the era "
                    "spread is narrow for a timeline game."
                )
            if track_count >= 12 and metrics.distinct_decades < 3:
                concerns.append(
                    f"Only {metrics.distinct_decades} decade(s) across "
                    f"{track_count} tracks; era coverage is thin."
                )
            if track_count >= 10 and metrics.distinct_years < track_count * 0.5:
                concerns.append(
                    f"Only {metrics.distinct_years} distinct years across "
                    f"{track_count} tracks; release years are clustered."
                )

        if track_count >= 8 and metrics.artist_diversity < 0.7:
            concerns.append(
                f"Low artist diversity: {metrics.distinct_artists} distinct "
                f"artists for {track_count} tracks."
            )

        no_year_threshold = max(3, round(track_count * 0.25))
        if metrics.tracks_without_year >= no_year_threshold:
            concerns.append(
                f"{metrics.tracks_without_year} tracks have no release year, "
                "which weakens a timeline game and can hide era skew."
            )

        return concerns

    async def _request_critique(
        self,
        tracks: list[DeckDraftTrack],
        metrics: DeckReviewMetrics,
        concerns: list[str],
        brief: str | None,
    ) -> DeckCritique:
        response = await self._llm.call(
            [
                SystemMessage(content=_SYSTEM_PROMPT),
                UserMessage(
                    content=self._render_prompt(tracks, metrics, concerns, brief)
                ),
            ],
            output_format=DeckCritique,
        )
        return response.completion

    def _render_prompt(
        self,
        tracks: list[DeckDraftTrack],
        metrics: DeckReviewMetrics,
        concerns: list[str],
        brief: str | None,
    ) -> str:
        metric_lines = [
            f"Target deck size: {metrics.target_size}",
            f"Tracks in deck: {metrics.track_count}",
            f"Distinct artists: {metrics.distinct_artists}",
            f"Distinct decades: {metrics.distinct_decades}",
            f"Distinct years: {metrics.distinct_years}",
            f"Tracks without a year: {metrics.tracks_without_year}",
        ]
        if metrics.top_artist is not None:
            metric_lines.append(
                f"Most frequent artist: {metrics.top_artist} "
                f"({metrics.top_artist_count}x, {metrics.top_artist_share:.0%})"
            )
        if metrics.top_decade is not None:
            metric_lines.append(
                f"Most frequent decade: {metrics.top_decade}s "
                f"({metrics.top_decade_count}x, {metrics.top_decade_share:.0%})"
            )

        concern_block = (
            "\n".join(f"- {concern}" for concern in concerns)
            if concerns
            else "- None detected by the static checks."
        )
        ordered_tracks = sorted(tracks, key=_track_sort_key)
        track_block = "\n".join(_render_track_line(track) for track in ordered_tracks)
        brief_block = (
            brief.strip()
            if brief and brief.strip()
            else ("(no conversation context available)")
        )

        return (
            "User brief / conversation so far (what the user actually wants — use "
            "this to decide whether any concentration is intended):\n"
            + brief_block
            + "\n\nDeck metrics:\n"
            + "\n".join(metric_lines)
            + "\n\nAutomatically detected concentration concerns "
            "(these are heuristics; ignore them where the brief asks for a niche "
            "deck):\n"
            + concern_block
            + "\n\nFull track list, ordered by release year (undated tracks last):\n"
            + track_block
        )

    def _render_critique(
        self,
        metrics: DeckReviewMetrics,
        concerns: list[str],
        critique: DeckCritique,
    ) -> str:
        header = (
            f"Deck review — {metrics.track_count} tracks "
            f"(target {metrics.target_size}), {metrics.distinct_artists} artists, "
            f"{metrics.distinct_decades} decades, {metrics.distinct_years} "
            "distinct years."
        )
        flags = (
            "Detected concentration:\n"
            + "\n".join(f"- {concern}" for concern in concerns)
            if concerns
            else "Static checks found no obvious concentration."
        )
        verdict = f"Critic assessment: {critique.assessment}"
        refine = (
            f"Refinement recommended: {'yes' if critique.needs_refinement else 'no'}"
        )
        if critique.suggestions:
            suggestions = "Suggestions:\n" + "\n".join(
                f"- [{suggestion.issue}] {suggestion.action}"
                for suggestion in critique.suggestions
            )
        else:
            suggestions = "Suggestions: none."
        return "\n".join([header, flags, verdict, refine, suggestions])


_SYSTEM_PROMPT = (
    "You are a strict music-curation critic for a Hitster timeline party game "
    "deck. In Hitster players guess the release year of each song, so a good "
    "deck spreads across many years and ideally several decades while staying "
    "recognizable, fun, and occasionally surprising.\n"
    "You receive deck metrics, automatically detected concentration concerns, "
    "and the full track list. Judge: (1) artist concentration — no single "
    "artist should dominate; (2) temporal coverage — tracks should span "
    "multiple years and decades, not cluster in one window; (3) artist and "
    "genre diversity; (4) presence of pleasant surprises and left-and-right "
    "picks that still fit; (5) overall balance relative to the target deck "
    "size.\n"
    "Be concrete: every suggestion must name the offending artist or era and a "
    "clear action the deck builder can take directly (remove a specific track, "
    "replace an over-represented pick from era Z with an earlier or later one, "
    "add coverage for decade W). Describe the gap to fill rather than inventing "
    "exact replacement tracks. Only flag things that genuinely hurt the deck; "
    "if it is already balanced, say so and set needs_refinement to false.\n"
    "Always weigh your judgment against the user's brief. If the user explicitly "
    "asked for a narrow or niche deck (a single artist, a single era or decade, "
    "or a tight genre or scene), treat the resulting concentration as intended "
    "and do NOT flag it as a problem — the statically detected concerns are then "
    "expected. In that case focus on variety and coverage WITHIN the allowed "
    "boundary: spread across the years available inside the niche, sub-genres, "
    "and surprising-but-fitting deep cuts. Only push back on concentration when "
    "it actually conflicts with what the user asked for. Respond in English."
)


def _primary_artist(artist: str) -> str:
    return artist.split(",")[0].strip() or "Unknown artist"


def _track_sort_key(track: DeckDraftTrack) -> tuple[int, str]:
    # Undated tracks sort last; ties broken by title for a stable order.
    return (track.year if track.year is not None else 10_000, track.title)


def _render_track_line(track: DeckDraftTrack) -> str:
    year = str(track.year) if track.year else "n/a"
    return f"- {year} · {track.artist} — {track.title}"
