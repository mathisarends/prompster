import asyncio
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from backend.features.oauth_connections.application import (
    SpotifyConnectionNotFoundException,
    SpotifyOAuthProvider,
    SpotifyTokenRevokedException,
    SpotifyTokenService,
)
from backend.features.oauth_connections.application.schemas import (
    SpotifyTokens,
    SpotifyUserProfile,
)
from backend.features.oauth_connections.domain import (
    OAuthConnection,
    OAuthConnectionRepository,
    OAuthProvider,
)


class _OAuthConnectionRepositoryStub(OAuthConnectionRepository):
    def __init__(self, *, connection: OAuthConnection | None) -> None:
        self.connection = connection
        self.deleted = False
        self.saved_connection: OAuthConnection | None = None

    async def get(
        self,
        *,
        user_id: UUID,
        provider: OAuthProvider,
    ) -> OAuthConnection | None:
        return self.connection

    async def save(self, *, connection: OAuthConnection) -> OAuthConnection:
        self.saved_connection = connection
        self.connection = connection
        return connection

    async def delete(self, *, user_id: UUID, provider: OAuthProvider) -> bool:
        self.deleted = True
        self.connection = None
        return True

    async def exists(self, *, user_id: UUID, provider: OAuthProvider) -> bool:
        return self.connection is not None


class _SpotifyOAuthProviderStub(SpotifyOAuthProvider):
    def __init__(
        self, *, tokens: SpotifyTokens | None = None, raises: bool = False
    ) -> None:
        self._tokens = tokens
        self._raises = raises
        self.received_refresh_token: str | None = None

    def build_authorization_url(self, *, state: str) -> str:
        raise AssertionError(
            "build_authorization_url is not used in token service tests"
        )

    async def exchange_code_for_tokens(
        self, *, authorization_code: str
    ) -> SpotifyTokens:
        raise AssertionError(
            "exchange_code_for_tokens is not used in token service tests"
        )

    async def fetch_spotify_user_profile(
        self, *, access_token: str
    ) -> SpotifyUserProfile:
        raise AssertionError(
            "fetch_spotify_user_profile is not used in token service tests"
        )

    async def refresh_access_token(self, *, refresh_token: str) -> SpotifyTokens:
        self.received_refresh_token = refresh_token
        if self._raises:
            raise ValueError("invalid_grant")
        assert self._tokens is not None
        return self._tokens


def _make_connection(*, refresh_token: str) -> OAuthConnection:
    return OAuthConnection.restore(
        id=uuid4(),
        created_at=datetime.now(UTC),
        user_id=uuid4(),
        provider=OAuthProvider.SPOTIFY,
        provider_user_id="spotify-user-1",
        refresh_token=refresh_token,
        scope="scope-1",
        connected_at=datetime.now(UTC),
    )


class TestSpotifyTokenService:
    def test_get_valid_access_token_raises_when_connection_missing(self) -> None:
        repository = _OAuthConnectionRepositoryStub(connection=None)
        provider = _SpotifyOAuthProviderStub(
            tokens=SpotifyTokens(
                access_token="access-1",
                refresh_token=None,
                expires_in=3600,
                scope="scope-1",
                token_type="Bearer",
            )
        )
        service = SpotifyTokenService(
            connection_repository=repository,
            spotify_oauth_provider=provider,
        )

        with pytest.raises(SpotifyConnectionNotFoundException):
            asyncio.run(service.get_valid_access_token(user_id=uuid4()))

    def test_get_valid_access_token_deletes_connection_when_refresh_revoked(
        self,
    ) -> None:
        connection = _make_connection(refresh_token="refresh-1")
        repository = _OAuthConnectionRepositoryStub(connection=connection)
        provider = _SpotifyOAuthProviderStub(raises=True)
        service = SpotifyTokenService(
            connection_repository=repository,
            spotify_oauth_provider=provider,
        )

        with pytest.raises(SpotifyTokenRevokedException):
            asyncio.run(service.get_valid_access_token(user_id=connection.user_id))

        assert repository.deleted is True

    def test_get_valid_access_token_rotates_refresh_token_when_returned(self) -> None:
        connection = _make_connection(refresh_token="refresh-1")
        repository = _OAuthConnectionRepositoryStub(connection=connection)
        provider = _SpotifyOAuthProviderStub(
            tokens=SpotifyTokens(
                access_token="access-2",
                refresh_token="refresh-2",
                expires_in=3000,
                scope="scope-2",
                token_type="Bearer",
            )
        )
        service = SpotifyTokenService(
            connection_repository=repository,
            spotify_oauth_provider=provider,
        )

        token = asyncio.run(service.get_valid_access_token(user_id=connection.user_id))

        assert token.access_token == "access-2"
        assert token.expires_in == 3000
        assert token.scope == "scope-2"
        assert provider.received_refresh_token == "refresh-1"
        assert repository.saved_connection is connection
        assert connection.refresh_token == "refresh-2"
