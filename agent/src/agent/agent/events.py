import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from agent.tools.views import AskFollowUpQuestion
from agent.workspace import PlaylistDraft


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
class ToolCallEvent(AgentEvent):
    tool_call_id: str
    name: str
    args: dict[str, Any]


@dataclass(kw_only=True)
class ToolResultEvent(AgentEvent):
    tool_call_id: str
    name: str
    result: str


@dataclass(kw_only=True)
class WorkspaceUpdatedEvent(AgentEvent):
    playlist_draft: PlaylistDraft


@dataclass(kw_only=True)
class FollowUpRequestedEvent(AgentEvent):
    tool_call_id: str
    questions: list[AskFollowUpQuestion]


@dataclass(kw_only=True)
class RunCompletedEvent(AgentEvent):
    output: str
