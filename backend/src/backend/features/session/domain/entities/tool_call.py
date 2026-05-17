from enum import StrEnum

from backend.features.session.domain.exceptions import (
    ToolCallAlreadyResolvedError,
)


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
