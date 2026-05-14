from datetime import datetime
from enum import StrEnum
from typing import Self
from uuid import UUID

from backend.shared.ddd import Entity


class MessageRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class ToolFunction:
    def __init__(self, name: str, arguments: dict[str, object]) -> None:
        self.name = name
        self.arguments = arguments


class ToolCall:
    def __init__(self, id: str, function: ToolFunction) -> None:
        self.id = id
        self.type = "function"
        self.function = function

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        import json

        return cls(
            id=data["id"],
            function=ToolFunction(
                name=data["function"]["name"],
                arguments=json.loads(data["function"]["arguments"]),
            ),
        )


class SessionMessage(Entity):
    def __init__(
        self,
        role: MessageRole,
        content: str,
        tool_calls: list[ToolCall] | None = None,
        tool_call_id: str | None = None,
        id: UUID | None = None,
        created_time: datetime | None = None,
    ) -> None:
        super().__init__(id=id, created_time=created_time)
        self.role = role
        self.content = content
        self.tool_calls = tool_calls
        self.tool_call_id = tool_call_id
