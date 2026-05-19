import asyncio
from uuid import UUID, uuid4

import pytest

from backend.features.auth.application.exceptions import SessionInvalidException
from backend.features.user.application.user_service import UserService
from backend.features.user.domain import User, UserRepository


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


class TestUserService:
    def test_get_me_raises_when_user_is_missing(self) -> None:
        repository = _UserRepositoryStub(user=None)
        service = UserService(user_repository=repository)

        with pytest.raises(SessionInvalidException, match="Invalid user"):
            asyncio.run(service.get_me(user_id=uuid4()))

    def test_get_me_returns_user_when_existing(self) -> None:
        user = User(
            name="Mathis",
            email="mathis@example.com",
            google_subject="google-sub-1",
            id=uuid4(),
        )
        repository = _UserRepositoryStub(user=user)
        service = UserService(user_repository=repository)

        result = asyncio.run(service.get_me(user_id=user.id))

        assert result is user
        assert repository.received_user_id == user.id
