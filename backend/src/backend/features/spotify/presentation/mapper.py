from backend.features.spotify.application.ports import (
    SpotifyAlbum,
    SpotifyArtist,
    SpotifyPlaylist,
    SpotifyTrack,
)
from backend.features.spotify.presentation.schemas import (
    SpotifyAlbumResponse,
    SpotifyArtistResponse,
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


def to_spotify_artist_response(artist: SpotifyArtist) -> SpotifyArtistResponse:
    return SpotifyArtistResponse(
        id=artist.id,
        name=artist.name,
        genres=artist.genres,
        followers=artist.followers,
        popularity=artist.popularity,
        image_url=artist.image_url,
    )


def to_spotify_album_response(album: SpotifyAlbum) -> SpotifyAlbumResponse:
    return SpotifyAlbumResponse(
        id=album.id,
        name=album.name,
        artist=album.artist,
        year=album.year,
        cover_url=album.cover_url,
        total_tracks=album.total_tracks,
    )
