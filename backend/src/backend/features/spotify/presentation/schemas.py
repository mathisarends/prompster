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
