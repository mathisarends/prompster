from datetime import datetime
from uuid import UUID

from collections.abc import Sequence

from backend.features.session.domain.entities.tool_call import (
    CompletedCall,
    FailedCall,
    PendingCall,
    ToolCall,
    ToolResultItem,
    is_pending,
    is_resolved,
)
from backend.features.session.domain.exceptions import (
    ToolCallAlreadyResolvedError,
    ToolCallNotFoundError,
)
from backend.shared.ddd import Entity


class ToolCallSequence(Entity):
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
        return all(not is_pending(call) for call in self.calls)

    @property
    def pending_calls(self) -> list[PendingCall]:
        return [call for call in self.calls if isinstance(call, PendingCall)]

    def add(self, call: PendingCall) -> PendingCall:
        self.calls.append(call)
        return call

    def remove_last_pending(self) -> PendingCall | None:
        for index in range(len(self.calls) - 1, -1, -1):
            call = self.calls[index]
            if isinstance(call, PendingCall):
                return self.calls.pop(index)
        return None

    def resolve(
        self,
        tool_call_id: str,
        result: str,
        items: Sequence[ToolResultItem] = (),
    ) -> CompletedCall:
        index, pending = self._require_pending(tool_call_id)
        completed = CompletedCall(
            id=pending.id,
            function=pending.function,
            result=result,
            items=tuple(items),
        )
        self.calls[index] = completed
        return completed

    def fail(self, tool_call_id: str, error: str) -> FailedCall:
        index, pending = self._require_pending(tool_call_id)
        failed = FailedCall(id=pending.id, function=pending.function, error=error)
        self.calls[index] = failed
        return failed

    def get(self, tool_call_id: str) -> ToolCall:
        for call in self.calls:
            if call.id == tool_call_id:
                return call
        raise ToolCallNotFoundError(
            f"No tool call {tool_call_id!r} in sequence {self.id}."
        )

    def _require_pending(self, tool_call_id: str) -> tuple[int, PendingCall]:
        for index, call in enumerate(self.calls):
            if call.id != tool_call_id:
                continue
            if is_resolved(call):
                state = "completed" if isinstance(call, CompletedCall) else "failed"
                raise ToolCallAlreadyResolvedError(
                    f"Tool call {tool_call_id!r} is already {state}."
                )
            return index, call
        raise ToolCallNotFoundError(
            f"No tool call {tool_call_id!r} in sequence {self.id}."
        )
