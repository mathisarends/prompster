from backend.features.chat.application import ChatDTO
from backend.features.chat.presentation.schemas import ChatResponseSchema


def to_chat_response_schema(chat: ChatDTO) -> ChatResponseSchema:
	return ChatResponseSchema(
		id=chat.id,
		title=chat.title,
		system_prompt=chat.system_prompt,
		created_at=chat.created_at,
		updated_at=chat.updated_at,
	)

