from collections.abc import AsyncIterator

from llmify import AssistantMessage as LLMAssistantMessage
from llmify import ChatModel, SystemMessage
from llmify import UserMessage as LLMUserMessage

from backend.features.session.application.ports.session_runner import SessionRunner
from backend.features.session.domain import (
    AssistantMessage,
    Session,
    UserMessage,
)


class LLMSessionRunner(SessionRunner):
    def __init__(self, llm: ChatModel, system_prompt: str) -> None:
        self._llm = llm
        self._system_prompt = system_prompt

    async def run(self, *, session: Session) -> AsyncIterator[str]:
        messages = [SystemMessage(content=self._system_prompt)]
        for entry in session.entries:
            if isinstance(entry, UserMessage):
                messages.append(LLMUserMessage(content=entry.content))
            elif isinstance(entry, AssistantMessage):
                messages.append(LLMAssistantMessage(content=entry.content))
        async for chunk in self._llm.stream(messages):
            yield chunk
