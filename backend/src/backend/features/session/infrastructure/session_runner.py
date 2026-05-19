from collections.abc import AsyncIterator

from llmify import AssistantMessage, ChatModel, SystemMessage, UserMessage

from backend.features.session.application.ports.session_runner import SessionRunner
from backend.features.session.domain import MessageRole, Session


class LLMSessionRunner(SessionRunner):
    def __init__(self, llm: ChatModel, system_prompt: str) -> None:
        self._llm = llm
        self._system_prompt = system_prompt

    async def run(self, *, session: Session) -> AsyncIterator[str]:
        messages = [SystemMessage(content=self._system_prompt)]
        for msg in session.messages:
            if msg.role == MessageRole.USER:
                messages.append(UserMessage(content=msg.content))
            elif msg.role == MessageRole.ASSISTANT:
                messages.append(AssistantMessage(content=msg.content))
        async for chunk in self._llm.stream(messages):
            yield chunk
