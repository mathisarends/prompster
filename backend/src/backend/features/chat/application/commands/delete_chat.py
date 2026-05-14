from uuid import UUID

from backend.features.chat.application.exceptions import ChatNotFoundApplicationError
from backend.features.chat.domain import ChatNotFoundError, ChatRepository


class DeleteChatHandler:
    def __init__(self, chat_repository: ChatRepository) -> None:
        self._chat_repository = chat_repository

    async def handle(self, *, chat_id: UUID) -> None:
        try:
            await self._chat_repository.delete(chat_id=chat_id)
        except ChatNotFoundError as exc:
            raise ChatNotFoundApplicationError from exc
