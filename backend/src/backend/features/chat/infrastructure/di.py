from dishka import Provider, Scope, provide

from backend.features.chat.application import (
	CreateChatHandler,
	DeleteChatHandler,
	GetChatByIdHandler,
	UpdateChatHandler,
)
from backend.features.chat.domain import ChatRepository
from backend.features.chat.infrastructure.orm import InMemoryChatRepository


class ChatProvider(Provider):
	@provide(scope=Scope.APP)
	def provide_chat_repository(self) -> ChatRepository:
		return InMemoryChatRepository()

	@provide(scope=Scope.REQUEST)
	def provide_create_chat_handler(
		self,
		chat_repository: ChatRepository,
	) -> CreateChatHandler:
		return CreateChatHandler(chat_repository=chat_repository)

	@provide(scope=Scope.REQUEST)
	def provide_get_chat_by_id_handler(
		self,
		chat_repository: ChatRepository,
	) -> GetChatByIdHandler:
		return GetChatByIdHandler(chat_repository=chat_repository)

	@provide(scope=Scope.REQUEST)
	def provide_update_chat_handler(
		self,
		chat_repository: ChatRepository,
	) -> UpdateChatHandler:
		return UpdateChatHandler(chat_repository=chat_repository)

	@provide(scope=Scope.REQUEST)
	def provide_delete_chat_handler(
		self,
		chat_repository: ChatRepository,
	) -> DeleteChatHandler:
		return DeleteChatHandler(chat_repository=chat_repository)

