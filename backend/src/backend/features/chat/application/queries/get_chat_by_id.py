from uuid import UUID

from backend.features.chat.application.dto import ChatDTO
from backend.features.chat.application.exceptions import ChatNotFoundApplicationError
from backend.features.chat.domain import ChatNotFoundError, ChatRepository


class GetChatByIdHandler:
    def __init__(self, chat_repository: ChatRepository) -> None:
        self._chat_repository = chat_repository

    async def handle(self, *, chat_id: UUID) -> ChatDTO:
        try:
            chat = await self._chat_repository.get_by_id(chat_id=chat_id)
        except ChatNotFoundError as exc:
            raise ChatNotFoundApplicationError from exc

        return ChatDTO(
            id=chat.id,
            title=chat.title,
            system_prompt=chat.system_prompt,
            created_at=chat.created_at,
            updated_at=chat.updated_at,
        )
