from abc import ABC, abstractmethod
from uuid import UUID

from backend.features.oauth_connections.domain.oauth_connection import (
    OAuthConnection,
    OAuthProvider,
)


class OAuthConnectionRepository(ABC):
    @abstractmethod
    async def get(
        self,
        *,
        user_id: UUID,
        provider: OAuthProvider,
    ) -> OAuthConnection | None: ...

    @abstractmethod
    async def save(self, *, connection: OAuthConnection) -> OAuthConnection: ...

    @abstractmethod
    async def delete(self, *, user_id: UUID, provider: OAuthProvider) -> bool: ...

    @abstractmethod
    async def exists(self, *, user_id: UUID, provider: OAuthProvider) -> bool: ...
