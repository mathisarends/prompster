from typing import Protocol
from uuid import UUID

from backend.features.auth.domain.user import AuthUser


class AuthUserRepository(Protocol):
    async def get_by_id(self, *, user_id: UUID) -> AuthUser | None: ...

    async def get_by_email(self, *, email: str) -> AuthUser | None: ...

    async def create(self, *, user: AuthUser) -> AuthUser: ...
