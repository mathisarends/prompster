from backend.presentation.schema import Schema


class SpotifyTrackResponse(Schema):
    id: str
    title: str
    artist: str
    album: str | None = None
    year: int | None = None
    cover_url: str | None = None
    preview_url: str | None = None


class SpotifyTrackSearchResponse(Schema):
    items: list[SpotifyTrackResponse]


class SpotifyPlaylistResponse(Schema):
    id: str
    name: str
    owner: str | None = None
    cover_url: str | None = None
    total_tracks: int | None = None


class SpotifyPlaylistSearchResponse(Schema):
    items: list[SpotifyPlaylistResponse]


class SpotifyArtistResponse(Schema):
    id: str
    name: str
    genres: list[str]
    followers: int | None = None
    popularity: int | None = None
    image_url: str | None = None


class SpotifyUnifiedSearchResponse(Schema):
    tracks: list[SpotifyTrackResponse]
    playlists: list[SpotifyPlaylistResponse]
    artists: list[SpotifyArtistResponse]
