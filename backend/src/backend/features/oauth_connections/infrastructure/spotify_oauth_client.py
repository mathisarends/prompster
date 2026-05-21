import base64
from urllib.parse import urlencode

import httpx
from pydantic import ValidationError

from backend.features.oauth_connections.application.ports import SpotifyOAuthProvider
from backend.features.oauth_connections.application.schemas import SpotifyTokens
from backend.features.oauth_connections.infrastructure.spotify_auth_settings import (
    SpotifyAuthSettings,
)
from backend.features.oauth_connections.infrastructure.spotify_scopes import (
    SPOTIFY_SCOPE_STRING,
)


class SpotifyOAuthClient(SpotifyOAuthProvider):
    def __init__(self, settings: SpotifyAuthSettings) -> None:
        self._settings = settings

    def build_authorization_url(self, *, state: str) -> str:
        self._validate_configuration()

        normalized_state = state.strip()
        if not normalized_state:
            raise ValueError("OAuth state must not be empty")

        query = urlencode(
            {
                "client_id": self._settings.client_id,
                "response_type": "code",
                "redirect_uri": self._settings.redirect_uri,
                "scope": SPOTIFY_SCOPE_STRING,
                "state": normalized_state,
                "show_dialog": "true",
            }
        )
        return f"{self._settings.authorization_endpoint}?{query}"

    async def exchange_code_for_tokens(
        self, *, authorization_code: str
    ) -> SpotifyTokens:
        self._validate_configuration()
        return await self._post_token(
            {
                "grant_type": "authorization_code",
                "code": authorization_code,
                "redirect_uri": self._settings.redirect_uri,
            }
        )

    async def refresh_access_token(self, *, refresh_token: str) -> SpotifyTokens:
        self._validate_configuration()
        return await self._post_token(
            {
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            }
        )

    async def fetch_spotify_user_id(self, *, access_token: str) -> str:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                self._settings.userinfo_endpoint,
                headers={"Authorization": f"Bearer {access_token}"},
            )

        if response.status_code >= 400:
            raise ValueError("Spotify /me request failed")

        spotify_user_id = response.json().get("id")
        if not isinstance(spotify_user_id, str) or not spotify_user_id:
            raise ValueError("Spotify /me response did not include id")

        return spotify_user_id

    def _validate_configuration(self) -> None:
        if not self._settings.client_id:
            raise ValueError("Spotify client ID is not configured")
        if not self._settings.client_secret:
            raise ValueError("Spotify client secret is not configured")
        if not self._settings.redirect_uri:
            raise ValueError("Spotify redirect URI is not configured")

    async def _post_token(self, form: dict[str, str]) -> SpotifyTokens:
        basic_auth = base64.b64encode(
            f"{self._settings.client_id}:{self._settings.client_secret}".encode("utf-8")
        ).decode("utf-8")

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                self._settings.token_endpoint,
                data=form,
                headers={
                    "Authorization": f"Basic {basic_auth}",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
            )

        if response.status_code >= 400:
            raise ValueError("Spotify token exchange failed")

        try:
            return SpotifyTokens.model_validate(response.json())
        except ValidationError as exc:
            raise ValueError("Spotify token payload is invalid") from exc
