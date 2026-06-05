import asyncio
import logging

import httpx

from backend.features.spotify.application.ports import (
    SpotifyPlaylistCreator as SpotifyPlaylistCreatorPort,
)

_RETRYABLE_STATUS_CODES = {429, 503}
_MAX_RETRIES = 3
_DEFAULT_BACKOFF_SECONDS = 1.0

logger = logging.getLogger(__name__)


class SpotifyPlaylistCreator(SpotifyPlaylistCreatorPort):
    _SPOTIFY_API_BASE_URL = "https://api.spotify.com/v1"

    def __init__(self) -> None:
        self._http_client = httpx.AsyncClient(
            base_url=self._SPOTIFY_API_BASE_URL,
            timeout=10.0,
        )

    async def aclose(self) -> None:
        await self._http_client.aclose()

    async def create_private_playlist(
        self,
        *,
        access_token: str,
        name: str,
        description: str,
    ) -> str:
        user_id = await self._get_current_user_id(access_token=access_token)
        data = await self._request_user_api(
            access_token=access_token,
            method="POST",
            path=f"/users/{user_id}/playlists",
            payload={
                "name": name,
                "description": description,
                "public": False,
            },
        )
        if not isinstance(data, dict):
            raise ValueError("Spotify playlist creation failed")

        playlist_id = data.get("id")
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
        await self._request_user_api(
            access_token=access_token,
            method="PUT",
            path=f"/playlists/{playlist_id}",
            payload={"name": name, "description": description},
        )

    async def replace_playlist_tracks(
        self,
        *,
        access_token: str,
        playlist_id: str,
        track_uris: list[str],
    ) -> None:
        await self._request_user_api(
            access_token=access_token,
            method="PUT",
            path=f"/playlists/{playlist_id}/tracks",
            payload={"uris": track_uris},
        )

    async def _get_current_user_id(self, *, access_token: str) -> str:
        data = await self._request_user_api(
            access_token=access_token,
            method="GET",
            path="/me",
        )
        if not isinstance(data, dict):
            raise ValueError("Spotify user lookup failed")

        user_id = data.get("id")
        if not isinstance(user_id, str) or not user_id.strip():
            raise ValueError("Spotify user lookup did not return an id")
        return user_id

    async def _request_user_api(
        self,
        *,
        access_token: str,
        method: str,
        path: str,
        payload: dict | None = None,
    ) -> dict | list | None:
        response = await self._send_with_retry(
            method=method,
            path=path,
            headers={"Authorization": f"Bearer {access_token}"},
            payload=payload,
        )

        if response.status_code >= 400:
            try:
                response_payload = response.json()
            except ValueError:
                response_payload = None

            detail = response.text
            if isinstance(response_payload, dict):
                error = response_payload.get("error")
                if isinstance(error, dict):
                    detail = str(error.get("message") or detail)
                elif isinstance(error, str) and error.strip():
                    detail = error
            raise ValueError(
                f"Spotify API request failed ({response.status_code}): {detail}"
            )

        if response.status_code == 204 or not response.content:
            return None

        try:
            return response.json()
        except ValueError as exc:
            raise ValueError("Spotify API response was not valid JSON") from exc

    async def _send_with_retry(
        self,
        *,
        method: str,
        path: str,
        headers: dict,
        payload: dict | None = None,
        retries: int = _MAX_RETRIES,
    ) -> httpx.Response:
        response: httpx.Response | None = None
        for attempt in range(retries + 1):
            response = await self._http_client.request(
                method=method,
                url=path,
                headers=headers,
                json=payload,
            )

            if (
                response.status_code not in _RETRYABLE_STATUS_CODES
                or attempt == retries
            ):
                return response

            retry_delay = _parse_retry_after(
                response.headers.get("Retry-After")
            ) or _DEFAULT_BACKOFF_SECONDS * (2**attempt)
            logger.warning(
                "Retrying Spotify user API request: method=%s path=%s "
                "status_code=%d retry_in_seconds=%s retry=%d/%d",
                method,
                path,
                response.status_code,
                retry_delay,
                attempt + 1,
                retries,
            )
            await asyncio.sleep(retry_delay)

        assert response is not None
        return response


def _parse_retry_after(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        return None
