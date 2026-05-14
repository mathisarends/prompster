from datetime import UTC, datetime
from uuid import uuid4

from backend.features.chat.domain import Chat, ChatRepository


class CreateChatHandler:
    def __init__(self, chat_repository: ChatRepository) -> None:
        self._chat_repository = chat_repository

    async def handle(self, *, title: str, system_prompt: str | None = None) -> Chat:
        now = datetime.now(UTC)
        chat = Chat(
            id=uuid4(),
            title=title,
            system_prompt=system_prompt,
            created_at=now,
            updated_at=now,
        )
        return await self._chat_repository.create(chat=chat)
