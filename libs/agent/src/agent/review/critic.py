import logging
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from harnessed import Agent
from harnessed.models import Model
from pydantic import BaseModel, Field

from agent.deck import Deck, DeckTrack
from agent.prompts import read_prompt

logger = logging.getLogger(__name__)


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


@dataclass(frozen=True, slots=True)
class DeckReviewMetrics:
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


@dataclass(frozen=True, slots=True)
class DeckReview:
    content: str
    triggered_llm: bool


class DeckCritic:
    """Review a deck for artist and era concentration.

    Static checks run first. Only a noticeably skewed deck is escalated to a
    one-shot harnessed agent that answers with a structured ``DeckCritique``.
    """

    def __init__(self, model: Model, *, target_size: int = 50) -> None:
        self._agent = Agent(
            model=model,
            instructions=read_prompt(Path(__file__).with_name("critic.md")),
        )
        self._target_size = target_size

    async def review(self, deck: Deck | None, *, brief: str = "") -> DeckReview:
        if deck is None or not deck.tracks:
            return DeckReview(
                content="No deck draft exists yet; nothing to review.",
                triggered_llm=False,
            )
        if len(deck.tracks) < _MIN_TRACKS_FOR_REVIEW:
            return DeckReview(
                content=(
                    f"Deck has only {len(deck.tracks)} track(s); too small for a "
                    "coverage review. Keep building first."
                ),
                triggered_llm=False,
            )

        metrics = _metrics(deck.tracks, self._target_size)
        concerns = _concerns(metrics)
        logger.info(
            "Deck review computed",
            extra={"track_count": metrics.track_count, "concerns": len(concerns)},
        )
        if not concerns:
            return DeckReview(
                content="\n".join(
                    [
                        _header(metrics),
                        "Static checks found no obvious concentration.",
                        "Refinement recommended: no",
                    ]
                ),
                triggered_llm=False,
            )

        result = await self._agent.run(
            _prompt(deck.tracks, metrics, concerns, brief), output=DeckCritique
        )
        return DeckReview(
            content=_render_critique(metrics, concerns, result.output),
            triggered_llm=True,
        )


# Below this many tracks a coverage review is not meaningful yet.
_MIN_TRACKS_FOR_REVIEW = 6


def _metrics(tracks: Sequence[DeckTrack], target: int) -> DeckReviewMetrics:
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
        top_artist_share=top_artist_count / track_count,
        top_decade=top_decade,
        top_decade_count=top_decade_count,
        top_decade_share=top_decade_count / len(years) if years else 0.0,
        artist_diversity=len(artist_counts) / track_count,
    )


def _concerns(metrics: DeckReviewMetrics) -> list[str]:
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


def _prompt(
    tracks: Sequence[DeckTrack],
    metrics: DeckReviewMetrics,
    concerns: list[str],
    brief: str,
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
    ordered = sorted(tracks, key=_track_sort_key)
    return (
        "User brief / conversation so far (what the user actually wants — use "
        "this to decide whether any concentration is intended):\n"
        + (brief.strip() or "(no conversation context available)")
        + "\n\nDeck metrics:\n"
        + "\n".join(metric_lines)
        + "\n\nAutomatically detected concentration concerns "
        "(these are heuristics; ignore them where the brief asks for a niche "
        "deck):\n"
        + "\n".join(f"- {concern}" for concern in concerns)
        + "\n\nFull track list, ordered by release year (undated tracks last):\n"
        + "\n".join(_render_track_line(track) for track in ordered)
    )


def _header(metrics: DeckReviewMetrics) -> str:
    return (
        f"Deck review — {metrics.track_count} tracks "
        f"(target {metrics.target_size}), {metrics.distinct_artists} artists, "
        f"{metrics.distinct_decades} decades, {metrics.distinct_years} "
        "distinct years."
    )


def _render_critique(
    metrics: DeckReviewMetrics,
    concerns: list[str],
    critique: DeckCritique,
) -> str:
    suggestions = (
        "Suggestions:\n"
        + "\n".join(
            f"- [{suggestion.issue}] {suggestion.action}"
            for suggestion in critique.suggestions
        )
        if critique.suggestions
        else "Suggestions: none."
    )
    return "\n".join(
        [
            _header(metrics),
            "Detected concentration:\n"
            + "\n".join(f"- {concern}" for concern in concerns),
            f"Critic assessment: {critique.assessment}",
            f"Refinement recommended: {'yes' if critique.needs_refinement else 'no'}",
            suggestions,
        ]
    )


def _primary_artist(artist: str) -> str:
    return artist.split(",")[0].strip() or "Unknown artist"


def _track_sort_key(track: DeckTrack) -> tuple[int, str]:
    # Undated tracks sort last; ties broken by title for a stable order.
    return (track.year if track.year is not None else 10_000, track.title)


def _render_track_line(track: DeckTrack) -> str:
    year = str(track.year) if track.year else "n/a"
    return f"- {year} · {track.artist} — {track.title}"
