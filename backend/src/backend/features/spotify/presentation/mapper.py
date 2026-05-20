from backend.features.spotify.application.ports import SpotifyPlaylist, SpotifyTrack
from backend.features.spotify.presentation.schemas import (
    SpotifyPlaylistResponse,
    SpotifyTrackResponse,
)


def to_spotify_track_response(track: SpotifyTrack) -> SpotifyTrackResponse:
    return SpotifyTrackResponse(
        id=track.id,
        title=track.title,
        artist=track.artist,
        album=track.album,
        year=track.year,
        cover_url=track.cover_url,
        preview_url=track.preview_url,
    )


def to_spotify_playlist_response(playlist: SpotifyPlaylist) -> SpotifyPlaylistResponse:
    return SpotifyPlaylistResponse(
        id=playlist.id,
        name=playlist.name,
        owner=playlist.owner,
        cover_url=playlist.cover_url,
        total_tracks=playlist.total_tracks,
    )
