from dataclasses import replace
from datetime import datetime
from uuid import UUID

from backend.features.chat.domain import ChatAggregate, ChatNotFoundError, ChatRepository


class InMemoryChatRepository(ChatRepository):
	def __init__(self) -> None:
		self._chats: dict[UUID, ChatAggregate] = {}

	async def get_by_id(self, *, chat_id: UUID) -> ChatAggregate:
		chat = self._chats.get(chat_id)
		if chat is None:
			raise ChatNotFoundError
		return chat

	async def create(self, *, chat: ChatAggregate) -> ChatAggregate:
		self._chats[chat.id] = chat
		return chat

	async def update(
		self,
		*,
		chat_id: UUID,
		title: str | None,
		system_prompt: str | None,
		updated_at: datetime,
	) -> ChatAggregate:
		chat = self._chats.get(chat_id)
		if chat is None:
			raise ChatNotFoundError

		updated_chat = replace(
			chat,
			title=title if title is not None else chat.title,
			system_prompt=system_prompt if system_prompt is not None else chat.system_prompt,
			updated_at=updated_at,
		)
		self._chats[chat_id] = updated_chat
		return updated_chat

	async def delete(self, *, chat_id: UUID) -> None:
		if chat_id not in self._chats:
			raise ChatNotFoundError
		del self._chats[chat_id]

