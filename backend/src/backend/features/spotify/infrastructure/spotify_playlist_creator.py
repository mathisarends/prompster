import logging

from spotifyify import RetryEvent, Spotifyify

from backend.features.spotify.application.ports import (
    SpotifyPlaylistCreator as SpotifyPlaylistCreatorPort,
)
from backend.features.spotify.application.retry_reporting import report_retry

logger = logging.getLogger(__name__)


class SpotifyPlaylistCreator(SpotifyPlaylistCreatorPort):
    def __init__(self, spotify: Spotifyify) -> None:
        self._spotify = spotify

    async def aclose(self) -> None:
        await self._spotify.close()

    async def create_private_playlist(
        self,
        *,
        access_token: str,
        name: str,
        description: str,
    ) -> str:
        async with self._spotify.session(
            access_token=access_token,
            on_retry=_log_spotifyify_retry,
        ):
            playlist = await self._spotify.playlists.create(
                name,
                public=False,
                description=description,
            )

        playlist_id = playlist.id
        if not isinstance(playlist_id, str) or not playlist_id.strip():
            raise ValueError("Spotify playlist creation did not return an id")
        return playlist_id

    async def update_playlist_details(
        self,
        *,
        access_token: str,
        playlist_id: str,
        name: str,
        description: str,
    ) -> None:
        async with self._spotify.session(
            access_token=access_token,
            on_retry=_log_spotifyify_retry,
        ):
            await self._spotify.playlists.update(
                playlist_id,
                name=name,
                description=description,
            )

    async def replace_playlist_tracks(
        self,
        *,
        access_token: str,
        playlist_id: str,
        track_uris: list[str],
    ) -> None:
        async with self._spotify.session(
            access_token=access_token,
            on_retry=_log_spotifyify_retry,
        ):
            await self._spotify.playlists.replace(playlist_id, track_uris)


def _log_spotifyify_retry(event: RetryEvent) -> None:
    logger.warning(
        "Retrying Spotifyify request: method=%s path=%s status_code=%d "
        "retry_in_seconds=%s retry=%d/%d",
        event.method.value,
        event.path,
        event.status_code,
        event.retry_in_seconds,
        event.retry_number,
        event.max_retries,
    )
    report_retry(event)
