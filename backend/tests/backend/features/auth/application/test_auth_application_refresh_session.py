import asyncio
from uuid import UUID, uuid4

import pytest

from backend.features.auth.application.refresh_session import (
    SessionRefresher,
)
from backend.features.auth.application.exceptions import SessionInvalidException
from backend.features.auth.application.ports import TokenIssuer
from backend.features.auth.application.schemas import (
    AuthSession,
    TokenPayload,
    TokenType,
)
from backend.features.user.domain import (
    AuthIdentity,
    AuthProvider,
    User,
    UserRepository,
)


class _UserRepositoryStub(UserRepository):
    def __init__(self, user: User | None) -> None:
        self._user = user
        self.received_user_id: UUID | None = None

    async def get_by_id(self, *, user_id: UUID) -> User | None:
        self.received_user_id = user_id
        return self._user

    async def delete_by_id(self, *, user_id: UUID) -> bool:
        return False

    async def count_sessions_for_user(self, *, user_id: UUID) -> int:
        return 0

    async def get_by_email(self, *, email: str) -> User | None:
        return None

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


class _TokenIssuerStub(TokenIssuer):
    def __init__(self, session: AuthSession) -> None:
        self._session = session
        self.received_user_id: UUID | None = None

    def create_session(self, user_id: UUID) -> AuthSession:
        self.received_user_id = user_id
        return self._session

    def validate(
        self,
        token: str,
        expected_type: TokenType = TokenType.ACCESS,
    ) -> TokenPayload:
        raise AssertionError("validate is not used in SessionRefresher tests")


class TestSessionRefresher:
    def test_handle_raises_when_user_does_not_exist(self) -> None:
        repository = _UserRepositoryStub(user=None)
        issuer = _TokenIssuerStub(AuthSession(access_token="a", refresh_token="r"))
        handler = SessionRefresher(user_repository=repository, token_issuer=issuer)

        with pytest.raises(SessionInvalidException, match="Invalid user"):
            asyncio.run(handler.refresh(user_id=uuid4()))

    def test_handle_returns_new_auth_session_for_existing_user(self) -> None:
        user = User(
            name="Mathis",
            email="mathis@example.com",
            id=uuid4(),
        )
        expected_session = AuthSession(access_token="access", refresh_token="refresh")
        repository = _UserRepositoryStub(user=user)
        issuer = _TokenIssuerStub(expected_session)
        handler = SessionRefresher(user_repository=repository, token_issuer=issuer)

        result = asyncio.run(handler.refresh(user_id=user.id))

        assert result == expected_session
        assert repository.received_user_id == user.id
        assert issuer.received_user_id == user.id
