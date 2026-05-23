from abc import ABC, abstractmethod
from uuid import UUID

from backend.features.user.domain.auth_identity import AuthIdentity, AuthProvider
from backend.features.user.domain.user import User


class UserRepository(ABC):
    @abstractmethod
    async def get_by_id(self, *, user_id: UUID) -> User | None: ...

    @abstractmethod
    async def get_by_email(self, *, email: str) -> User | None: ...

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
    async def create_with_auth_identity(
        self,
        *,
        user: User,
        auth_identity: AuthIdentity,
    ) -> User: ...
