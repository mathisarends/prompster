from typing import Protocol
from uuid import UUID

from backend.features.auth.domain.refresh_session import RefreshSession
from backend.features.auth.domain.user import AuthUser


class AuthUserRepository(Protocol):
    async def get_by_id(self, *, user_id: UUID) -> AuthUser | None: ...

    async def get_by_email(self, *, email: str) -> AuthUser | None: ...

    async def create(self, *, user: AuthUser) -> AuthUser: ...


class RefreshSessionRepository(Protocol):
    async def get_by_token(self, *, token: str) -> RefreshSession | None: ...

    async def save(self, *, refresh_session: RefreshSession) -> None: ...

    async def delete(self, *, token: str) -> None: ...
