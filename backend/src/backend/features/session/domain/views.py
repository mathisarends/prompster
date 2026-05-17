from datetime import datetime
from enum import StrEnum
from uuid import UUID

from backend.features.session.domain.exceptions import (
    ToolCallAlreadyResolvedError,
    ToolCallNotFoundError,
)
from backend.shared.ddd import Entity


class MessageRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"


class ToolCallState(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class ToolFunction:
    def __init__(self, name: str, arguments: dict[str, object]) -> None:
        self.name = name
        self.arguments = arguments


class ToolCall:
    def __init__(
        self,
        id: str,
        function: ToolFunction,
        state: ToolCallState = ToolCallState.PENDING,
        result: str | None = None,
        error: str | None = None,
    ) -> None:
        self.id = id
        self.function = function
        self.state = state
        self.result = result
        self.error = error

    @property
    def is_pending(self) -> bool:
        return self.state == ToolCallState.PENDING

    @property
    def is_resolved(self) -> bool:
        return self.state != ToolCallState.PENDING

    def complete(self, result: str) -> None:
        self._assert_pending()
        self.state = ToolCallState.COMPLETED
        self.result = result

    def fail(self, error: str) -> None:
        self._assert_pending()
        self.state = ToolCallState.FAILED
        self.error = error

    def _assert_pending(self) -> None:
        if self.is_resolved:
            raise ToolCallAlreadyResolvedError(
                f"Tool call {self.id!r} is already {self.state}."
            )


class ToolCallGroup(Entity):
    def __init__(
        self,
        calls: list[ToolCall],
        id: UUID | None = None,
        created_time: datetime | None = None,
    ) -> None:
        super().__init__(id=id, created_time=created_time)
        self.calls = calls

    @property
    def is_complete(self) -> bool:
        return all(call.is_resolved for call in self.calls)

    @property
    def pending_calls(self) -> list[ToolCall]:
        return [call for call in self.calls if call.is_pending]

    def resolve(self, tool_call_id: str, result: str) -> ToolCall:
        call = self._get(tool_call_id)
        call.complete(result)
        return call

    def fail(self, tool_call_id: str, error: str) -> ToolCall:
        call = self._get(tool_call_id)
        call.fail(error)
        return call

    def _get(self, tool_call_id: str) -> ToolCall:
        for call in self.calls:
            if call.id == tool_call_id:
                return call
        raise ToolCallNotFoundError(
            f"No tool call {tool_call_id!r} in group {self.id}."
        )


class SessionMessage(Entity):
    def __init__(
        self,
        role: MessageRole,
        content: str,
        tool_call_group: ToolCallGroup | None = None,
        id: UUID | None = None,
        created_time: datetime | None = None,
    ) -> None:
        super().__init__(id=id, created_time=created_time)
        self.role = role
        self.content = content
        self.tool_call_group = tool_call_group
