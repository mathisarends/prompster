import asyncio
from uuid import UUID, uuid4

import pytest

from backend.features.auth.application.exceptions import SessionInvalidException
from backend.features.user.application.user_service import UserService
from backend.features.user.domain import User, UserRepository
from backend.features.oauth_connections.domain import (
    OAuthConnection,
    OAuthConnectionRepository,
    OAuthProvider,
)


class _UserRepositoryStub(UserRepository):
    def __init__(self, user: User | None) -> None:
        self._user = user
        self.received_user_id: UUID | None = None

    async def get_by_id(self, *, user_id: UUID) -> User | None:
        self.received_user_id = user_id
        return self._user

    async def get_by_email(self, *, email: str) -> User | None:
        return None

    async def create(self, *, user: User) -> User:
        return user


class _OAuthConnectionRepositoryStub(OAuthConnectionRepository):
    def __init__(self, *, exists_result: bool) -> None:
        self._exists_result = exists_result
        self.received_user_id: UUID | None = None
        self.received_provider: OAuthProvider | None = None

    async def get(
        self,
        *,
        user_id: UUID,
        provider: OAuthProvider,
    ) -> OAuthConnection | None:
        return None

    async def save(self, *, connection: OAuthConnection) -> OAuthConnection:
        return connection

    async def delete(self, *, user_id: UUID, provider: OAuthProvider) -> bool:
        return False

    async def exists(self, *, user_id: UUID, provider: OAuthProvider) -> bool:
        self.received_user_id = user_id
        self.received_provider = provider
        return self._exists_result


class TestUserService:
    def test_get_me_raises_when_user_is_missing(self) -> None:
        repository = _UserRepositoryStub(user=None)
        oauth_repository = _OAuthConnectionRepositoryStub(exists_result=False)
        service = UserService(
            user_repository=repository,
            oauth_connection_repository=oauth_repository,
        )

        with pytest.raises(SessionInvalidException, match="Invalid user"):
            asyncio.run(service.get_me(user_id=uuid4()))

    def test_get_me_returns_user_and_spotify_status_when_existing(self) -> None:
        user = User(
            name="Mathis",
            email="mathis@example.com",
            google_subject="google-sub-1",
            id=uuid4(),
        )
        repository = _UserRepositoryStub(user=user)
        oauth_repository = _OAuthConnectionRepositoryStub(exists_result=True)
        service = UserService(
            user_repository=repository,
            oauth_connection_repository=oauth_repository,
        )

        result = asyncio.run(service.get_me(user_id=user.id))

        assert result.user is user
        assert result.spotify_connected is True
        assert repository.received_user_id == user.id
        assert oauth_repository.received_user_id == user.id
        assert oauth_repository.received_provider == OAuthProvider.SPOTIFY
