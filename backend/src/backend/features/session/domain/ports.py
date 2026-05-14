from datetime import datetime
from typing import Protocol
from uuid import UUID

from .session import Session


class SessionRepository(Protocol):
    async def get_by_id(self, *, session_id: UUID) -> Session: ...

    async def create(self, *, session: Session) -> Session: ...

    async def update(
        self,
        *,
        session_id: UUID,
        title: str | None,
        system_prompt: str | None,
    ) -> Session: ...

    async def delete(self, *, session_id: UUID) -> None: ...
