from datetime import datetime
from typing import Protocol
from uuid import UUID

from .aggregate import ChatAggregate


class ChatRepository(Protocol):
    async def get_by_id(self, *, chat_id: UUID) -> ChatAggregate: ...

    async def create(self, *, chat: ChatAggregate) -> ChatAggregate: ...

    async def update(
        self,
        *,
        chat_id: UUID,
        title: str | None,
        system_prompt: str | None,
        updated_at: datetime,
    ) -> ChatAggregate: ...

    async def delete(self, *, chat_id: UUID) -> None: ...
