from datetime import datetime
from typing import Protocol
from uuid import UUID

from .chat import Chat


class ChatRepository(Protocol):
    async def get_by_id(self, *, chat_id: UUID) -> Chat: ...

    async def create(self, *, chat: Chat) -> Chat: ...

    async def update(
        self,
        *,
        chat_id: UUID,
        title: str | None,
        system_prompt: str | None,
        updated_at: datetime,
    ) -> Chat: ...

    async def delete(self, *, chat_id: UUID) -> None: ...
