from abc import ABC, abstractmethod
from uuid import UUID

from backend.features.user.domain.auth_identity import AuthIdentity, AuthProvider
from backend.features.user.domain.user import User


class UserRepository(ABC):
    @abstractmethod
    async def get_by_id(self, *, user_id: UUID) -> User | None: ...

    @abstractmethod
    async def delete_by_id(self, *, user_id: UUID) -> bool: ...

    @abstractmethod
    async def count_sessions_for_user(self, *, user_id: UUID) -> int: ...

    @abstractmethod
    async def get_by_auth_identity(
        self,
        *,
        provider: AuthProvider,
        subject: str,
    ) -> User | None: ...

    @abstractmethod
    async def create(self, *, user: User) -> User: ...

    @abstractmethod
    async def update(self, *, user: User) -> User: ...

    @abstractmethod
    async def create_with_auth_identity(
        self,
        *,
        user: User,
        auth_identity: AuthIdentity,
    ) -> User: ...
