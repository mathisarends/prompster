"""The compact XML-like tags the model reads tracks, playlists and decks in."""

from html import escape


def tag(name: str, attrs: list[tuple[str, str | None]]) -> str:
    """Render a self-closing tag and skip empty attributes."""
    rendered = " ".join(
        f'{key}="{escape(value, quote=True)}"' for key, value in attrs if value
    )
    return f"<{name} {rendered} />"


def release_label(artist: str, title: str, year: int | None) -> str:
    label = f"{artist} - {title}"
    if year:
        label = f"{label} ({year})"
    return label
