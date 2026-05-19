from typing import Any

from llmify import AssistantMessage, SystemMessage, ToolResultMessage, UserMessage


class MessageManager:
    def __init__(self, system_prompt: str) -> None:
        self._system_prompt = system_prompt
        self._messages: list[Any] = []
        self.reset()

    def all(self) -> list[Any]:
        return list(self._messages)

    def add_user(self, content: str) -> None:
        self._messages.append(UserMessage(content=content))

    def add_assistant(self, content: str, tool_calls: list[Any] | None = None) -> None:
        self._messages.append(
            AssistantMessage(content=content, tool_calls=tool_calls or [])
        )

    def add_tool_result(self, tool_call_id: str, content: str) -> None:
        self._messages.append(
            ToolResultMessage(tool_call_id=tool_call_id, content=content)
        )

    def reset(self) -> None:
        self._messages = [SystemMessage(content=self._system_prompt)]
