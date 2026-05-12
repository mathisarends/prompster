def normalize_spotify_id(value: str, resource_type: str) -> str:
    prefix = f"spotify:{resource_type}:"
    if value.startswith(prefix):
        return value[len(prefix) :]

    marker = f"/{resource_type}/"
    if marker in value:
        tail = value.split(marker, 1)[1]
        return tail.split("?", 1)[0].split("/", 1)[0]

    return value


def artist_names(artists) -> str:
    names = [a.name for a in (artists or []) if a and a.name]
    return ", ".join(names) if names else "Unknown artist"


def track_title(track) -> str:
    return track.name or "Unknown title"


def release_year(release_date: str | None) -> int:
    if release_date and len(release_date) >= 4 and release_date[:4].isdigit():
        return int(release_date[:4])
    return 0


def track_url(track) -> str:
    if track.external_urls and track.external_urls.spotify:
        return track.external_urls.spotify
    if track.uri and track.uri.startswith("spotify:track:"):
        track_id = track.uri.removeprefix("spotify:track:")
        return f"https://open.spotify.com/track/{track_id}"
    return ""


def playlist_url(playlist) -> str:
    if playlist.external_urls and playlist.external_urls.spotify:
        return playlist.external_urls.spotify
    if playlist.id:
        return f"https://open.spotify.com/playlist/{playlist.id}"
    return ""


def format_track(index: int, track, fallback_release_date: str | None = None) -> str:
    artists = track.artists or []
    artist_uris = ", ".join(a.uri for a in artists if a.uri)
    date = (
        track.album.release_date
        if track.album and track.album.release_date
        else fallback_release_date
    )
    return (
        f"{index}. {track_title(track)}"
        f" – {artist_names(artists)}"
        f" ({release_year(date)})"
        f"  uri={track.uri or 'n/a'}  artist_uris=[{artist_uris}]"
    )


def format_album(index: int, album) -> str:
    artists = album.artists or []
    return (
        f"{index}. {album.name} – {artist_names(artists)}"
        f" ({release_year(album.release_date)}, {album.total_tracks} tracks)"
        f"  uri={album.uri}"
    )


def chunked(items: list[str], size: int) -> list[list[str]]:
    return [items[i : i + size] for i in range(0, len(items), size)]
