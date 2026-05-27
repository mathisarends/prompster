from abc import ABC, abstractmethod
from uuid import UUID

from backend.features.user.domain.user_message_quota import UserMessageQuota


class UserMessageQuotaRepository(ABC):
    @abstractmethod
    async def get_or_create_for_update(self, *, user_id: UUID) -> UserMessageQuota:
        """Return quota row locked FOR UPDATE in the current transaction."""

    @abstractmethod
    async def get_by_user_id(self, *, user_id: UUID) -> UserMessageQuota | None:
        """Return quota row without locking."""

    @abstractmethod
    async def save(self, *, quota: UserMessageQuota) -> UserMessageQuota: ...
