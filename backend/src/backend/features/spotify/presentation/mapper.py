from backend.features.spotify.application.ports import SpotifyTrack
from backend.features.spotify.presentation.schemas import SpotifyTrackResponse


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
