import asyncio
import secrets
from uuid import UUID, uuid4

import pytest

from backend.features.oauth_connections.application.ports import (
    SpotifyOAuthProvider,
)
from backend.features.oauth_connections.application.schemas import (
    SpotifyAuthorizationRequest,
    SpotifyCallbackResult,
    SpotifyTokens,
    SpotifyUserProfile,
)
from backend.features.oauth_connections.application.spotify_oauth_connection_service import (
    SpotifyOAuthConnectionService,
)
from backend.features.oauth_connections.domain import (
    OAuthConnection,
    OAuthConnectionRepository,
)
from backend.shared.oauth_provider import OAuthProvider


class _OAuthConnectionRepositoryStub(OAuthConnectionRepository):
    def __init__(self, *, existing: OAuthConnection | None = None) -> None:
        self._existing = existing
        self.saved_connection: OAuthConnection | None = None

    async def get(
        self,
        *,
        user_id: UUID,
        provider: OAuthProvider,
    ) -> OAuthConnection | None:
        return self._existing

    async def save(self, *, connection: OAuthConnection) -> OAuthConnection:
        self.saved_connection = connection
        self._existing = connection
        return connection

    async def delete(self, *, user_id: UUID, provider: OAuthProvider) -> bool:
        return False

    async def exists(self, *, user_id: UUID, provider: OAuthProvider) -> bool:
        return self._existing is not None


class _SpotifyOAuthProviderStub(SpotifyOAuthProvider):
    def __init__(self) -> None:
        self.received_state: str | None = None
        self.received_authorization_code: str | None = None
        self.received_access_token: str | None = None
        self.tokens = SpotifyTokens(
            access_token="access-1",
            refresh_token="refresh-1",
            expires_in=3600,
            scope="scope-1",
            token_type="Bearer",
        )

    def build_authorization_url(self, *, state: str) -> str:
        self.received_state = state
        return f"https://accounts.spotify.com/authorize?state={state}"

    async def exchange_code_for_tokens(
        self, *, authorization_code: str
    ) -> SpotifyTokens:
        self.received_authorization_code = authorization_code
        return self.tokens

    async def fetch_spotify_user_profile(
        self, *, access_token: str
    ) -> SpotifyUserProfile:
        self.received_access_token = access_token
        return SpotifyUserProfile(
            spotify_user_id="spotify-user-1",
            is_premium=True,
        )

    async def refresh_access_token(self, *, refresh_token: str) -> SpotifyTokens:
        raise AssertionError(
            "refresh_access_token is not used in connect handler tests"
        )


class TestSpotifyOAuthConnectionService:
    def test_start_binds_user_id_into_state(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(secrets, "token_urlsafe", lambda _: "nonce-1")
        repository = _OAuthConnectionRepositoryStub()
        provider = _SpotifyOAuthProviderStub()
        service = SpotifyOAuthConnectionService(
            connection_repository=repository,
            spotify_oauth_provider=provider,
        )
        user_id = uuid4()

        result = service.start_connect(user_id=user_id)

        assert isinstance(result, SpotifyAuthorizationRequest)
        assert result.state == f"{user_id}:nonce-1"
        assert provider.received_state == result.state
        assert result.authorization_url.endswith(f"state={result.state}")

    def test_complete_returns_user_mismatch_when_state_user_differs(self) -> None:
        repository = _OAuthConnectionRepositoryStub()
        provider = _SpotifyOAuthProviderStub()
        service = SpotifyOAuthConnectionService(
            connection_repository=repository,
            spotify_oauth_provider=provider,
        )
        state_user_id = uuid4()
        state = f"{state_user_id}:nonce-1"

        result = asyncio.run(
            service.complete_connect(
                authenticated_user_id=uuid4(),
                code="code-1",
                state=state,
                error=None,
                expected_oauth_state=state,
            )
        )

        assert result == SpotifyCallbackResult.error(reason="user_mismatch")

    def test_complete_saves_connection_and_returns_success(self) -> None:
        repository = _OAuthConnectionRepositoryStub()
        provider = _SpotifyOAuthProviderStub()
        service = SpotifyOAuthConnectionService(
            connection_repository=repository,
            spotify_oauth_provider=provider,
        )
        user_id = uuid4()
        state = f"{user_id}:nonce-1"

        result = asyncio.run(
            service.complete_connect(
                authenticated_user_id=user_id,
                code="code-1",
                state=state,
                error=None,
                expected_oauth_state=state,
            )
        )

        assert result == SpotifyCallbackResult.success()
        assert provider.received_authorization_code == "code-1"
        assert provider.received_access_token == "access-1"
        assert repository.saved_connection is not None
        assert repository.saved_connection.user_id == user_id
        assert repository.saved_connection.provider == OAuthProvider.SPOTIFY
        assert repository.saved_connection.provider_user_id == "spotify-user-1"
        assert repository.saved_connection.refresh_token == "refresh-1"
        assert repository.saved_connection.is_premium is True
