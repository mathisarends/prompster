from collections.abc import Callable

from pydantic import BaseModel
from spotifyify import (
    Image,
    Playlist,
    SimplifiedAlbum,
    SimplifiedArtist,
    SimplifiedPlaylist,
    Track,
)

from agent.deck import DeckDraftTrack
from agent.messages.rendering import (
    render_album_tag,
    render_playlist_tag,
    render_track_tag,
)


class SpotifyTrackLookupResult(BaseModel):
    content: str
    tracks: list[DeckDraftTrack]


class SpotifyPlaylistPreview(BaseModel):
    name: str
    cover_url: str | None = None


def track_release_date(track: Track) -> str | None:
    return track.album.release_date if track.album else None


def track_cover_url(track: Track) -> str | None:
    return cover_url(track.album.images) if track.album else None


def cover_url(images: list[Image] | None) -> str | None:
    if not images:
        return None
    return images[0].url


def track_lookup_result(
    tracks: list[Track],
    *,
    release_date_for: Callable[[Track], str | None],
    cover_url_for: Callable[[Track], str | None],
) -> SpotifyTrackLookupResult:
    lines: list[str] = []
    draft_tracks: list[DeckDraftTrack] = []

    for _, track in enumerate(tracks):
        release_date = release_date_for(track)
        cover_url = cover_url_for(track)
        draft_track = _deck_draft_track(track, release_date, cover_url)
        if draft_track.spotify_uri is not None:
            draft_tracks.append(draft_track)
            lines.append(
                render_track_tag(
                    draft_track,
                    identity_attr="uri",
                    identity_value=draft_track.spotify_uri,
                )
            )

    return SpotifyTrackLookupResult(content="\n".join(lines), tracks=draft_tracks)


def format_album(album: SimplifiedAlbum) -> str:
    return render_album_tag(
        uri=album.uri,
        name=album.name,
        artist=_artist_names(album.artists),
        year=_release_year(album.release_date),
        track_count=album.total_tracks,
    )


def format_playlist(playlist: Playlist | SimplifiedPlaylist) -> str:
    return render_playlist_tag(
        id=playlist.id,
        name=playlist.name,
        track_count=_playlist_track_count(playlist),
    )


def playlist_preview(
    playlist: Playlist | SimplifiedPlaylist,
) -> SpotifyPlaylistPreview:
    return SpotifyPlaylistPreview(
        name=playlist.name or "Unknown playlist",
        cover_url=cover_url(playlist.images),
    )


def _playlist_track_count(playlist: Playlist | SimplifiedPlaylist) -> int:
    tracks = playlist.items or playlist.tracks
    return tracks.total if tracks and tracks.total is not None else 0


def _artist_names(artists: list[SimplifiedArtist] | None) -> str:
    names = [artist.name for artist in (artists or []) if artist and artist.name]
    return ", ".join(names) if names else "Unknown artist"


def _track_title(track: Track) -> str:
    return track.name or "Unknown title"


def _release_year(release_date: str | None) -> int:
    if release_date and len(release_date) >= 4 and release_date[:4].isdigit():
        return int(release_date[:4])
    return 0


def _deck_draft_track(
    track: Track,
    release_date: str | None,
    cover_url: str | None,
) -> DeckDraftTrack:
    return DeckDraftTrack(
        title=_track_title(track),
        artist=_artist_names(track.artists),
        year=_release_year(release_date) or None,
        spotify_uri=(
            track.uri if track.uri and track.uri.startswith("spotify:track:") else None
        ),
        cover_url=cover_url,
    )
