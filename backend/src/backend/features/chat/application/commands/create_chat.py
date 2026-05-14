from datetime import UTC, datetime
from uuid import uuid4

from backend.features.chat.application.dto import ChatDTO
from backend.features.chat.domain import ChatAggregate, ChatRepository


class CreateChatHandler:
    def __init__(self, chat_repository: ChatRepository) -> None:
        self._chat_repository = chat_repository

    async def handle(self, *, title: str, system_prompt: str | None = None) -> ChatDTO:
        now = datetime.now(UTC)
        chat = ChatAggregate(
            id=uuid4(),
            title=title,
            system_prompt=system_prompt,
            created_at=now,
            updated_at=now,
        )
        created_chat = await self._chat_repository.create(chat=chat)
        return ChatDTO(
            id=created_chat.id,
            title=created_chat.title,
            system_prompt=created_chat.system_prompt,
            created_at=created_chat.created_at,
            updated_at=created_chat.updated_at,
        )
