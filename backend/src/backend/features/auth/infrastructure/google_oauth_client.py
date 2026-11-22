from urllib.parse import urlencode

import httpx
from pydantic import ValidationError

from backend.features.auth.application.ports import GoogleOAuthProvider
from backend.features.auth.domain import GoogleIdentity
from backend.features.auth.infrastructure.google_auth_settings import GoogleAuthSettings


class GoogleOAuthClient(GoogleOAuthProvider):
    def __init__(self, google_auth_settings: GoogleAuthSettings) -> None:
        self._google_auth_settings = google_auth_settings

    def build_authorization_url(self, *, state: str) -> str:
        self._validate_configuration()

        normalized_state = state.strip()
        if not normalized_state:
            raise ValueError("OAuth state must not be empty")

        query = urlencode(
            {
                "client_id": self._google_auth_settings.client_id,
                "redirect_uri": self._google_auth_settings.redirect_uri,
                "response_type": "code",
                "scope": self._google_auth_settings.scope,
                "state": normalized_state,
            }
        )
        return f"{self._google_auth_settings.authorization_endpoint}?{query}"

    async def exchange_code_for_identity(
        self,
        *,
        authorization_code: str,
    ) -> GoogleIdentity:
        self._validate_configuration()

        access_token = await self._exchange_code_for_access_token(
            authorization_code=authorization_code,
        )
        return await self._get_identity(access_token=access_token)

    def _validate_configuration(self) -> None:
        if not self._google_auth_settings.client_id:
            raise ValueError("Google client ID is not configured")
        if not self._google_auth_settings.client_secret.get_secret_value():
            raise ValueError("Google client secret is not configured")
        if not self._google_auth_settings.redirect_uri:
            raise ValueError("Google redirect URI is not configured")

    async def _exchange_code_for_access_token(self, *, authorization_code: str) -> str:
        payload = {
            "code": authorization_code,
            "client_id": self._google_auth_settings.client_id,
            "client_secret": self._google_auth_settings.client_secret.get_secret_value(),
            "redirect_uri": self._google_auth_settings.redirect_uri,
            "grant_type": "authorization_code",
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                self._google_auth_settings.token_endpoint,
                data=payload,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

        if response.status_code >= 400:
            raise ValueError("Google token exchange failed")

        token_payload = response.json()
        access_token = token_payload.get("access_token")
        if not isinstance(access_token, str) or not access_token:
            raise ValueError("Google token response did not include access token")

        return access_token

    async def _get_identity(self, *, access_token: str) -> GoogleIdentity:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                self._google_auth_settings.userinfo_endpoint,
                headers={"Authorization": f"Bearer {access_token}"},
            )

        if response.status_code >= 400:
            raise ValueError("Google user info request failed")

        user_payload = response.json()
        try:
            return GoogleIdentity.model_validate(user_payload)
        except ValidationError as exc:
            raise ValueError("Google user info payload is invalid") from exc
