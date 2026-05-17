import secrets

import pytest

from backend.features.auth.application.commands.google_login import GoogleLoginHandler
from backend.features.auth.application.ports import GoogleOAuthProvider
from backend.features.auth.application.schemas import (
    GoogleAuthorizationRequest,
    GoogleIdentity,
)


class _GoogleOAuthProviderStub(GoogleOAuthProvider):
    def __init__(self) -> None:
        self.received_state: str | None = None

    def build_authorization_url(self, *, state: str) -> str:
        self.received_state = state
        return f"https://accounts.google.com/o/oauth2/auth?state={state}"

    async def exchange_code_for_identity(
        self,
        *,
        authorization_code: str,
    ) -> GoogleIdentity:
        raise AssertionError("Google login must not exchange an authorization code")


class TestGoogleLoginHandler:
    def test_handle_generates_oauth_state_and_builds_authorization_request(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(secrets, "token_urlsafe", lambda _: "state-123")
        provider = _GoogleOAuthProviderStub()
        handler = GoogleLoginHandler(google_oauth_provider=provider)

        result = handler.handle()

        assert isinstance(result, GoogleAuthorizationRequest)
        assert result.state == "state-123"
        assert result.authorization_url.endswith("state=state-123")
        assert provider.received_state == "state-123"
