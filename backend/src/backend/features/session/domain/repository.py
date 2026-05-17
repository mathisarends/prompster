from abc import ABC, abstractmethod
from uuid import UUID

from backend.features.session.domain.session import Session


class SessionRepository(ABC):
    @abstractmethod
    async def get_by_id(self, session_id: UUID) -> Session: ...

    @abstractmethod
    async def create(self, session: Session) -> Session: ...

    @abstractmethod
    async def update(
        self,
        session_id: UUID,
        title: str | None,
    ) -> Session: ...

    @abstractmethod
    async def delete(self, session_id: UUID) -> None: ...
