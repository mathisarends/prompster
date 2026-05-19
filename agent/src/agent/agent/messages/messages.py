from pathlib import Path

from llmify import (
    AssistantMessage,
    Message,
    SystemMessage,
    ToolCall,
    ToolResultMessage,
    UserMessage,
)

_SYSTEM_PROMPT = (Path(__file__).parent / "prompts" / "system_prompt.md").read_text(
    encoding="utf-8"
)


class MessageManager:
    def __init__(self, system_prompt: str | None = None) -> None:
        self._system_prompt = system_prompt or _SYSTEM_PROMPT
        self._messages: list[Message] = []
        self.reset()

    def all(self) -> list[Message]:
        return list(self._messages)

    def add_user(self, content: str) -> None:
        self._messages.append(UserMessage(content=content))

    def add_assistant(
        self, content: str, tool_calls: list[ToolCall] | None = None
    ) -> None:
        self._messages.append(
            AssistantMessage(content=content, tool_calls=tool_calls or [])
        )

    def add_tool_result(self, tool_call_id: str, content: str) -> None:
        self._messages.append(
            ToolResultMessage(tool_call_id=tool_call_id, content=content)
        )

    def reset(self) -> None:
        self._messages = [SystemMessage(content=self._system_prompt)]
