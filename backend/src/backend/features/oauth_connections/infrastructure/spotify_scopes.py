from enum import StrEnum


class SpotifyScope(StrEnum):
    USER_READ_PRIVATE = "user-read-private"
    USER_READ_EMAIL = "user-read-email"
    PLAYLIST_MODIFY_PUBLIC = "playlist-modify-public"
    PLAYLIST_MODIFY_PRIVATE = "playlist-modify-private"
    STREAMING = "streaming"
    USER_READ_PLAYBACK_STATE = "user-read-playback-state"
    USER_MODIFY_PLAYBACK_STATE = "user-modify-playback-state"


REQUIRED_SPOTIFY_SCOPES: tuple[SpotifyScope, ...] = (
    SpotifyScope.USER_READ_PRIVATE,
    SpotifyScope.USER_READ_EMAIL,
    SpotifyScope.PLAYLIST_MODIFY_PUBLIC,
    SpotifyScope.PLAYLIST_MODIFY_PRIVATE,
    SpotifyScope.STREAMING,
    SpotifyScope.USER_READ_PLAYBACK_STATE,
    SpotifyScope.USER_MODIFY_PLAYBACK_STATE,
)

SPOTIFY_SCOPE_STRING: str = " ".join(REQUIRED_SPOTIFY_SCOPES)
