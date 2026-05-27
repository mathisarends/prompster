from html import escape

from agent.playlist.views import PlaylistDraftTrack


def render_track_tag(
    track: PlaylistDraftTrack,
    *,
    identity_attr: str = "id",
    identity_value: str | None = None,
    include_pinned: bool = False,
) -> str:
    attrs = [
        (identity_attr, identity_value or str(track.id)),
        ("label", _render_track_label(track)),
    ]
    if include_pinned and track.is_pinned:
        attrs.append(("pinned", "true"))
    return f"<track {_render_attrs(attrs)} />"


def render_album_tag(
    *,
    uri: str | None,
    name: str,
    artist: str,
    year: int | None,
    track_count: int | None,
) -> str:
    attrs = [
        ("uri", uri),
        ("label", _render_release_label(artist, name, year)),
        ("tracks", str(track_count) if track_count is not None else None),
    ]
    return f"<album {_render_attrs(attrs)} />"


def render_playlist_tag(
    *,
    id: str | None,
    name: str,
    track_count: int | None,
) -> str:
    attrs = [
        ("id", id),
        ("label", name),
        ("tracks", str(track_count) if track_count is not None else None),
    ]
    return f"<playlist {_render_attrs(attrs)} />"


def _render_track_label(track: PlaylistDraftTrack) -> str:
    return _render_release_label(track.artist, track.title, track.year)


def _render_release_label(artist: str, title: str, year: int | None) -> str:
    label = f"{artist} - {title}"
    if year:
        label = f"{label} ({year})"
    return label


def _render_attrs(attrs: list[tuple[str, str | None]]) -> str:
    return " ".join(
        f'{name}="{escape(value, quote=True)}"'
        for name, value in attrs
        if value is not None and value != ""
    )
