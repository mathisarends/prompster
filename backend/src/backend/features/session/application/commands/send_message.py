from collections.abc import AsyncIterator

from backend.features.session.domain import Session, SessionRepository
from backend.features.session.domain.views import MessageRole
from llmify import AssistantMessage, ChatOpenAI, UserMessage, Message


class SendMessageHandler:
    def __init__(
        self,
        llm: ChatOpenAI,
        session_repository: SessionRepository,
    ) -> None:
        self._llm = llm
        self._session_repository = session_repository

    async def stream_response(
        self,
        *,
        session: Session,
        content: str,
    ) -> AsyncIterator[str]:
        session.add_user_message(content=content)
        await self._session_repository.create(session=session)

        chunks: list[str] = []
        async for chunk in self._llm.stream(self._build_context(session)):
            if not chunk:
                continue
            chunks.append(chunk)
            yield chunk

        if completion := "".join(chunks).strip():
            session.add_assistant_message(content=completion)
            await self._session_repository.create(session=session)

    def _build_context(self, session: Session) -> list[Message]:
        messages: list[Message] = []

        role_map = {
            MessageRole.USER: UserMessage,
            MessageRole.ASSISTANT: AssistantMessage,
        }

        for message in session.messages:
            if message_cls := role_map.get(message.role):
                messages.append(message_cls(content=message.content))

        return messages
