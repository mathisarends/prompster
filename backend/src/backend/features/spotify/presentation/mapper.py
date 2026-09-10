from backend.features.spotify.application.ports import (
    SpotifyArtist,
    SpotifyPlaylist,
    SpotifyTrack,
    SpotifyUnifiedSearchResult,
)
from backend.features.spotify.presentation.schemas import (
    SpotifyArtistResponse,
    SpotifyPlaylistResponse,
    SpotifyTrackResponse,
    SpotifyUnifiedSearchResponse,
)


def to_spotify_track_response(track: SpotifyTrack) -> SpotifyTrackResponse:
    return SpotifyTrackResponse(
        id=track.id,
        title=track.title,
        artist=track.artist,
        album=track.album,
        year=track.year,
        cover_url=track.cover_url,
        url=track.url,
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


def to_spotify_unified_search_response(
    search_result: SpotifyUnifiedSearchResult,
) -> SpotifyUnifiedSearchResponse:
    return SpotifyUnifiedSearchResponse(
        tracks=[to_spotify_track_response(track) for track in search_result.tracks],
        playlists=[
            to_spotify_playlist_response(playlist)
            for playlist in search_result.playlists
        ],
        artists=[
            to_spotify_artist_response(artist) for artist in search_result.artists
        ],
    )
