import asyncio
from uuid import UUID, uuid4

import pytest

from backend.features.auth.application.exceptions import SessionInvalidException
from backend.features.user.application.user_service import UserService
from backend.features.user.domain import (
    AuthIdentity,
    AuthProvider,
    SpotifyAccount,
    User,
    UserRepository,
)


class _UserRepositoryStub(UserRepository):
    def __init__(self, user: User | None) -> None:
        self._user = user
        self.received_user_id: UUID | None = None
        self.received_delete_user_id: UUID | None = None
        self.received_count_user_id: UUID | None = None
        self.delete_result = user is not None
        self.session_count = 0

    async def get_by_id(self, *, user_id: UUID) -> User | None:
        self.received_user_id = user_id
        return self._user

    async def delete_by_id(self, *, user_id: UUID) -> bool:
        self.received_delete_user_id = user_id
        return self.delete_result

    async def count_sessions_for_user(self, *, user_id: UUID) -> int:
        self.received_count_user_id = user_id
        return self.session_count

    async def get_by_auth_identity(
        self,
        *,
        provider: AuthProvider,
        subject: str,
    ) -> User | None:
        return None

    async def create(self, *, user: User) -> User:
        return user

    async def update(self, *, user: User) -> User:
        return user

    async def create_with_auth_identity(
        self,
        *,
        user: User,
        auth_identity: AuthIdentity,
    ) -> User:
        return user


class TestUserService:
    def test_get_me_raises_when_user_is_missing(self) -> None:
        repository = _UserRepositoryStub(user=None)
        service = UserService(user_repository=repository)

        with pytest.raises(SessionInvalidException, match="Invalid user"):
            asyncio.run(service.get_me(user_id=uuid4()))

    def test_get_me_returns_user_and_spotify_status_when_existing(self) -> None:
        user = User(
            name="Mathis",
            spotify=SpotifyAccount.connected_with(is_premium=True),
            id=uuid4(),
        )
        repository = _UserRepositoryStub(user=user)
        service = UserService(user_repository=repository)

        result = asyncio.run(service.get_me(user_id=user.id))

        assert result is user
        assert result.spotify.connected is True
        assert result.spotify.is_premium is True
        assert repository.received_user_id == user.id

    def test_delete_me_raises_when_user_is_missing(self) -> None:
        repository = _UserRepositoryStub(user=None)
        service = UserService(user_repository=repository)

        with pytest.raises(SessionInvalidException, match="Invalid user"):
            asyncio.run(service.delete_me(user_id=uuid4()))

    def test_delete_me_deletes_existing_user(self) -> None:
        user = User(
            name="Mathis",
            id=uuid4(),
        )
        repository = _UserRepositoryStub(user=user)
        service = UserService(user_repository=repository)

        asyncio.run(service.delete_me(user_id=user.id))

        assert repository.received_delete_user_id == user.id

    def test_get_delete_information_raises_when_user_is_missing(self) -> None:
        repository = _UserRepositoryStub(user=None)
        service = UserService(user_repository=repository)

        with pytest.raises(SessionInvalidException, match="Invalid user"):
            asyncio.run(service.get_delete_information(user_id=uuid4()))

    def test_get_delete_information_returns_session_count(self) -> None:
        user = User(
            name="Mathis",
            id=uuid4(),
        )
        repository = _UserRepositoryStub(user=user)
        repository.session_count = 7
        service = UserService(user_repository=repository)

        result = asyncio.run(service.get_delete_information(user_id=user.id))

        assert result.session_count == 7
        assert repository.received_user_id == user.id
        assert repository.received_count_user_id == user.id
