from spotifyify import Image, Spotifyify, Track

from backend.features.session.application.ports.spotify_track_search import (
    SpotifyTrack,
    SpotifyTrackSearch,
)


class SpotifyifyTrackSearch(SpotifyTrackSearch):
    def __init__(self, spotify: Spotifyify) -> None:
        self._spotify = spotify

    async def search(self, *, query: str, limit: int = 20) -> list[SpotifyTrack]:
        normalized_query = query.strip()
        if not normalized_query:
            return []

        result = await self._spotify.tracks.find(normalized_query, limit=limit)
        return [
            _to_spotify_track(track)
            for track in result.items or []
            if track.id and track.name
        ]


def _to_spotify_track(track: Track) -> SpotifyTrack:
    album = track.album
    artists = ", ".join(artist.name for artist in track.artists or [] if artist.name)
    return SpotifyTrack(
        id=track.id or "",
        title=track.name or "",
        artist=artists,
        album=album.name if album else None,
        year=_release_year(album.release_date if album else None),
        cover_url=_cover_url(album.images if album else None),
        preview_url=track.preview_url,
    )


def _release_year(release_date: str | None) -> int | None:
    if not release_date:
        return None

    year = release_date.split("-", maxsplit=1)[0]
    try:
        return int(year)
    except ValueError:
        return None


def _cover_url(images: list[Image] | None) -> str | None:
    if not images:
        return None
    return images[0].url
