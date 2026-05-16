from collections.abc import AsyncIterator

from backend.features.session.domain import Session
from backend.features.session.domain.views import MessageRole
from llmify import AssistantMessage, ChatOpenAI, SystemMessage, UserMessage, Message


class SendMessageHandler:
    def __init__(
        self,
        llm: ChatOpenAI,
    ) -> None:
        self._llm = llm

    async def stream_response(
        self,
        *,
        session: Session,
        content: str,
    ) -> AsyncIterator[str]:
        session.add_user_message(content=content)

        chunks: list[str] = []
        async for chunk in self._llm.stream(self._build_context(session)):
            if not chunk:
                continue
            chunks.append(chunk)
            yield chunk

        if completion := "".join(chunks).strip():
            session.add_assistant_message(content=completion)

    def _build_context(self, session: Session) -> list[Message]:
        messages: list[Message] = []

        if session.system_prompt:
            messages.append(SystemMessage(content=session.system_prompt))

        role_map = {
            MessageRole.USER: UserMessage,
            MessageRole.ASSISTANT: AssistantMessage,
        }

        for message in session.messages:
            if message_cls := role_map.get(message.role):
                messages.append(message_cls(content=message.content))

        return messages
