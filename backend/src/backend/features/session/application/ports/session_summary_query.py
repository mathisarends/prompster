from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class SessionSummary:
    id: UUID
    title: str
    is_starred: bool
    created_at: datetime
    last_activity_at: datetime


class SessionSummaryQuery(ABC):
    @abstractmethod
    async def list_for_owner(
        self,
        *,
        owner_id: UUID,
        limit: int,
        offset: int,
    ) -> list[SessionSummary]: ...

    @abstractmethod
    async def search_for_owner(
        self,
        *,
        owner_id: UUID,
        query: str,
        limit: int,
        offset: int,
    ) -> list[SessionSummary]: ...
