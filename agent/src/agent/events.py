from __future__ import annotations
import time
import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from agent.playlist import PlaylistDraft, PlaylistDraftUpdate

if TYPE_CHECKING:
    from agent.tools.views import ActionType


@dataclass(kw_only=True)
class AgentEvent:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)


@dataclass(kw_only=True)
class RunStartedEvent(AgentEvent):
    message: str


@dataclass(kw_only=True)
class StepStartedEvent(AgentEvent):
    step: int


@dataclass(kw_only=True)
class AssistantMessageEvent(AgentEvent):
    content: str


@dataclass(kw_only=True)
class AssistantMessageChunkEvent(AgentEvent):
    chunk: str


@dataclass(kw_only=True)
class ToolCallEvent(AgentEvent):
    tool_call_id: str
    name: str
    args: dict[str, Any]
    status_label: str | None = None
    action_type: ActionType | None = None


@dataclass(kw_only=True)
class ToolResultEvent(AgentEvent):
    tool_call_id: str
    name: str
    result: str


@dataclass(kw_only=True)
class SuspendedForInputEvent(AgentEvent):
    question: str | None = None
    options: list[str] = field(default_factory=list)
    is_last_question: bool = False


@dataclass(kw_only=True)
class WorkspaceUpdatedEvent(AgentEvent):
    playlist_draft: PlaylistDraft
    update: PlaylistDraftUpdate


@dataclass(kw_only=True)
class RunCompletedEvent(AgentEvent):
    output: str
