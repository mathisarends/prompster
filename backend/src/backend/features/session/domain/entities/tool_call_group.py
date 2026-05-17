from datetime import datetime
from uuid import UUID

from backend.features.session.domain.entities.tool_call import ToolCall
from backend.features.session.domain.exceptions import ToolCallNotFoundError
from backend.shared.ddd import Entity


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
