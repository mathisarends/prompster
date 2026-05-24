from urllib.parse import urlencode

from backend.features.oauth_connections.application.schemas import SpotifyTokens
from backend.features.oauth_connections.infrastructure.spotify_oauth_client import (
    SpotifyOAuthClient,
)
from backend.features.oauth_connections.infrastructure.spotify_scopes import (
    SPOTIFY_SCOPE_STRING,
)


class SpotifyLoginOAuthClient(SpotifyOAuthClient):
    """Spotify OAuth client for the SSO login flow.

    Uses login_redirect_uri instead of redirect_uri and omits show_dialog
    so returning users are not forced to re-consent on every login.
    """

    def build_authorization_url(self, *, state: str) -> str:
        normalized_state = state.strip()
        if not normalized_state:
            raise ValueError("OAuth state must not be empty")

        query = urlencode(
            {
                "client_id": self._settings.client_id,
                "response_type": "code",
                "redirect_uri": self._settings.login_redirect_uri,
                "scope": SPOTIFY_SCOPE_STRING,
                "state": normalized_state,
            }
        )
        return f"{self._settings.authorization_endpoint}?{query}"

    async def exchange_code_for_tokens(
        self, *, authorization_code: str
    ) -> SpotifyTokens:
        return await self._post_token(
            {
                "grant_type": "authorization_code",
                "code": authorization_code,
                "redirect_uri": self._settings.login_redirect_uri,
            }
        )
