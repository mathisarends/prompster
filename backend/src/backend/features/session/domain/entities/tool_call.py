from dataclasses import dataclass
from enum import StrEnum


class ToolActionType(StrEnum):
    SEARCH = "search"
    FETCH = "fetch"
    MUTATE = "mutate"
    INTERACT = "interact"


@dataclass(frozen=True)
class ToolFunction:
    name: str
    arguments: dict[str, object]
    status_label: str | None = None
    action_type: ToolActionType | None = None


@dataclass(frozen=True)
class PendingCall:
    id: str
    function: ToolFunction


@dataclass(frozen=True)
class CompletedCall:
    id: str
    function: ToolFunction
    result: str


@dataclass(frozen=True)
class FailedCall:
    id: str
    function: ToolFunction
    error: str


type ResolvedCall = CompletedCall | FailedCall
type ToolCall = PendingCall | ResolvedCall


def is_pending(call: ToolCall) -> bool:
    return isinstance(call, PendingCall)


def is_resolved(call: ToolCall) -> bool:
    return not is_pending(call)
