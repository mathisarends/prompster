from collections import Counter
from collections.abc import Sequence
from html import escape

from agent.deck.views import Deck, DeckTrack
from agent.markup import release_label, tag


def render_deck_state(deck: Deck | None, *, max_tracks: int) -> str:
    """Render the live deck for the end of a model request.

    It is appended to each request instead of stored in the history, so the
    model always sees the current deck and the cached prompt prefix stays stable.
    """
    if deck is None or not deck.tracks:
        return f'<deck_state track_count="0" max_tracks="{max_tracks}" />'

    track_count = len(deck.tracks)
    lines = [
        (
            f'<deck_state id="{deck.id}" '
            f'name="{escape(deck.name, quote=True)}" '
            f'track_count="{track_count}" '
            f'max_tracks="{max_tracks}" '
            f'remaining_tracks="{max(0, max_tracks - track_count)}">'
        ),
        _render_coverage(deck.tracks),
    ]
    lines.extend(
        tag(
            "track",
            [
                ("id", track.id),
                ("label", release_label(track.artist, track.title, track.year)),
            ],
        )
        for track in deck.tracks
    )
    lines.append("</deck_state>")
    return "\n".join(lines)


def _render_coverage(tracks: Sequence[DeckTrack]) -> str:
    years = [track.year for track in tracks if track.year]
    decades = Counter((year // 10) * 10 for year in years)
    artists = Counter(track.artist.split(",")[0].strip() for track in tracks)
    top_artist, top_artist_count = artists.most_common(1)[0]
    return tag(
        "coverage",
        [
            (
                "decades",
                ", ".join(
                    f"{decade}s: {count}" for decade, count in sorted(decades.items())
                ),
            ),
            ("undated", str(len(tracks) - len(years))),
            ("artists", str(len(artists))),
            ("top_artist", f"{top_artist} ({top_artist_count})"),
        ],
    )
