from uuid import UUID

from backend.features.chat.application.exceptions import ChatNotFoundApplicationError
from backend.features.chat.domain import Chat, ChatNotFoundError, ChatRepository


class GetChatByIdHandler:
    def __init__(self, chat_repository: ChatRepository) -> None:
        self._chat_repository = chat_repository

    async def handle(self, *, chat_id: UUID) -> Chat:
        try:
            chat = await self._chat_repository.get_by_id(chat_id=chat_id)
        except ChatNotFoundError as exc:
            raise ChatNotFoundApplicationError from exc

        return chat
