from backend.presentation import Schema


class SpotifyAccessTokenResponse(Schema):
    access_token: str
    expires_in: int
    scope: str
