from collections.abc import AsyncIterator

from backend.features.session.domain import MessageRole, Session, SessionRepository
from llmify import AssistantMessage, ChatModel, UserMessage, Message


class SendMessageHandler:
    def __init__(
        self,
        llm: ChatModel,
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
        latest_message = session.messages[-1] if session.messages else None
        should_append_user_message = not (
            latest_message is not None
            and latest_message.role == MessageRole.USER
            and latest_message.content == content
        )

        if should_append_user_message:
            session.add_user_message(content=content)
            await self._session_repository.save(session=session)

        chunks: list[str] = []
        async for chunk in self._llm.stream(self._build_context(session)):
            if not chunk:
                continue
            chunks.append(chunk)
            yield chunk

        if completion := "".join(chunks).strip():
            session.add_assistant_message(content=completion)
            await self._session_repository.save(session=session)

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
