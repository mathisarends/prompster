from datetime import UTC, datetime
from uuid import UUID

from backend.features.chat.application.exceptions import (
    ChatNotFoundApplicationError,
    ChatUpdateValidationError,
)
from backend.features.chat.domain import Chat, ChatNotFoundError, ChatRepository


class UpdateChatHandler:
    def __init__(self, chat_repository: ChatRepository) -> None:
        self._chat_repository = chat_repository

    async def handle(
        self,
        *,
        chat_id: UUID,
        title: str | None = None,
        system_prompt: str | None = None,
    ) -> Chat:
        if title is None and system_prompt is None:
            raise ChatUpdateValidationError(
                "At least one field must be provided for update"
            )

        try:
            updated_chat = await self._chat_repository.update(
                chat_id=chat_id,
                title=title,
                system_prompt=system_prompt,
                updated_at=datetime.now(UTC),
            )
        except ChatNotFoundError as exc:
            raise ChatNotFoundApplicationError from exc

        return updated_chat
