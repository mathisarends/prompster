import asyncio

import pytest

from backend.features.oauth_connections.infrastructure.spotify_auth_settings import (
    SpotifyAuthSettings,
)
from backend.features.oauth_connections.infrastructure.spotify_oauth_client import (
    SpotifyOAuthClient,
)


class _ResponseStub:
    def __init__(self, *, status_code: int, payload: object) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self) -> object:
        return self._payload


class AsyncClientStub:
    response: _ResponseStub

    def __init__(self, *, timeout: float) -> None:
        self.timeout = timeout

    async def __aenter__(self) -> "AsyncClientStub":
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: object | None,
    ) -> None:
        return None

    async def get(self, _url: str, *, headers: dict[str, str]) -> _ResponseStub:
        assert headers["Authorization"].startswith("Bearer ")
        return self.response


class TestSpotifyOAuthClient:
    @staticmethod
    def _settings() -> SpotifyAuthSettings:
        return SpotifyAuthSettings(
            client_id="client-id",
            client_secret="client-secret",
            redirect_uri="https://example.com/callback",
            userinfo_endpoint="https://example.com/me",
        )

    def test_fetch_spotify_user_profile_maps_premium_flag(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        AsyncClientStub.response = _ResponseStub(
            status_code=200,
            payload={"id": "spotify-user-1", "product": "premium"},
        )
        monkeypatch.setattr("httpx.AsyncClient", AsyncClientStub)
        client = SpotifyOAuthClient(settings=self._settings())

        profile = asyncio.run(client.fetch_spotify_user_profile(access_token="token-1"))

        assert profile.spotify_user_id == "spotify-user-1"
        assert profile.is_premium is True

    def test_fetch_spotify_user_profile_raises_on_invalid_payload(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        AsyncClientStub.response = _ResponseStub(
            status_code=200,
            payload={"product": "premium"},
        )
        monkeypatch.setattr("httpx.AsyncClient", AsyncClientStub)
        client = SpotifyOAuthClient(settings=self._settings())

        with pytest.raises(ValueError, match="Spotify /me payload is invalid"):
            asyncio.run(client.fetch_spotify_user_profile(access_token="token-1"))
