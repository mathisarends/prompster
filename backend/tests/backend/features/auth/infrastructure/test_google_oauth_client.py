import asyncio
from types import TracebackType
from typing import Self
from urllib.parse import parse_qs, urlparse

import pytest
from backend.features.auth.infrastructure.google_auth_settings import (
    GoogleAuthSettings,
)
from backend.features.auth.infrastructure.google_oauth_client import GoogleOAuthClient


class _ResponseStub:
    def __init__(self, *, status_code: int, payload: object) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self) -> object:
        return self._payload


class _AsyncClientStub:
    post_response: _ResponseStub
    get_response: _ResponseStub
    post_data: dict[str, str] | None = None
    get_headers: dict[str, str] | None = None

    def __init__(self, *, timeout: float) -> None:
        assert timeout == 10.0

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        return None

    async def post(
        self,
        _url: str,
        *,
        data: dict[str, str],
        headers: dict[str, str],
    ) -> _ResponseStub:
        assert headers == {"Content-Type": "application/x-www-form-urlencoded"}
        type(self).post_data = data
        return type(self).post_response

    async def get(self, _url: str, *, headers: dict[str, str]) -> _ResponseStub:
        type(self).get_headers = headers
        return type(self).get_response


class TestGoogleOAuthClient:
    @staticmethod
    def _settings(**overrides: str) -> GoogleAuthSettings:
        settings = {
            "google_client_id": "google-client-id",
            "google_client_secret": "google-client-secret",
            "google_redirect_uri": "https://app.example.com/auth/google/callback",
            "google_authorization_endpoint": "https://accounts.example.com/authorize",
            "google_token_endpoint": "https://accounts.example.com/token",
            "google_userinfo_endpoint": "https://accounts.example.com/userinfo",
        }
        settings.update(overrides)
        return GoogleAuthSettings(_env_file=None, **settings)

    def test_builds_authorization_url_with_required_oauth_parameters(self) -> None:
        client = GoogleOAuthClient(self._settings(google_scope="openid email"))

        authorization_url = client.build_authorization_url(state=" state-123 ")

        parsed_url = urlparse(authorization_url)
        assert parsed_url.geturl().startswith("https://accounts.example.com/authorize?")
        assert parse_qs(parsed_url.query) == {
            "client_id": ["google-client-id"],
            "redirect_uri": ["https://app.example.com/auth/google/callback"],
            "response_type": ["code"],
            "scope": ["openid email"],
            "state": ["state-123"],
        }

    @pytest.mark.parametrize(
        ("settings", "message"),
        [
            ({"google_client_id": ""}, "client ID"),
            ({"google_client_secret": ""}, "client secret"),
            ({"google_redirect_uri": ""}, "redirect URI"),
        ],
    )
    def test_rejects_incomplete_configuration(
        self,
        settings: dict[str, str],
        message: str,
    ) -> None:
        client = GoogleOAuthClient(self._settings(**settings))

        with pytest.raises(ValueError, match=message):
            client.build_authorization_url(state="state-123")

    def test_rejects_empty_state(self) -> None:
        client = GoogleOAuthClient(self._settings())

        with pytest.raises(ValueError, match="state must not be empty"):
            client.build_authorization_url(state="  ")

    def test_exchanges_code_and_maps_google_identity(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _AsyncClientStub.post_response = _ResponseStub(
            status_code=200,
            payload={"access_token": "access-token"},
        )
        _AsyncClientStub.get_response = _ResponseStub(
            status_code=200,
            payload={"sub": " google-subject ", "name": " Mathis ", "picture": " "},
        )
        _AsyncClientStub.post_data = None
        _AsyncClientStub.get_headers = None
        monkeypatch.setattr("httpx.AsyncClient", _AsyncClientStub)
        client = GoogleOAuthClient(self._settings())

        identity = asyncio.run(
            client.exchange_code_for_identity(authorization_code="code-123")
        )

        assert identity.subject == "google-subject"
        assert identity.name == "Mathis"
        assert identity.profile_image_url is None
        assert _AsyncClientStub.post_data == {
            "code": "code-123",
            "client_id": "google-client-id",
            "client_secret": "google-client-secret",
            "redirect_uri": "https://app.example.com/auth/google/callback",
            "grant_type": "authorization_code",
        }
        assert _AsyncClientStub.get_headers == {"Authorization": "Bearer access-token"}

    @pytest.mark.parametrize(
        ("token_response", "message"),
        [
            (_ResponseStub(status_code=400, payload={}), "token exchange failed"),
            (
                _ResponseStub(status_code=200, payload={}),
                "did not include access token",
            ),
        ],
    )
    def test_rejects_invalid_token_exchange_response(
        self,
        monkeypatch: pytest.MonkeyPatch,
        token_response: _ResponseStub,
        message: str,
    ) -> None:
        _AsyncClientStub.post_response = token_response
        _AsyncClientStub.get_response = _ResponseStub(status_code=200, payload={})
        monkeypatch.setattr("httpx.AsyncClient", _AsyncClientStub)
        client = GoogleOAuthClient(self._settings())

        with pytest.raises(ValueError, match=message):
            asyncio.run(
                client.exchange_code_for_identity(authorization_code="code-123")
            )

    @pytest.mark.parametrize(
        ("profile_response", "message"),
        [
            (_ResponseStub(status_code=500, payload={}), "user info request failed"),
            (
                _ResponseStub(status_code=200, payload={"sub": "  "}),
                "payload is invalid",
            ),
        ],
    )
    def test_rejects_invalid_userinfo_response(
        self,
        monkeypatch: pytest.MonkeyPatch,
        profile_response: _ResponseStub,
        message: str,
    ) -> None:
        _AsyncClientStub.post_response = _ResponseStub(
            status_code=200,
            payload={"access_token": "access-token"},
        )
        _AsyncClientStub.get_response = profile_response
        monkeypatch.setattr("httpx.AsyncClient", _AsyncClientStub)
        client = GoogleOAuthClient(self._settings())

        with pytest.raises(ValueError, match=message):
            asyncio.run(
                client.exchange_code_for_identity(authorization_code="code-123")
            )
