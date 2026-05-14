from backend.features.chat.domain import Chat
from backend.features.chat.presentation.schemas import ChatResponse


def to_chat_response(chat: Chat) -> ChatResponse:
    return ChatResponse(
        id=chat.id,
        title=chat.title,
        system_prompt=chat.system_prompt,
        created_at=chat.created_at,
        updated_at=chat.updated_at,
    )
