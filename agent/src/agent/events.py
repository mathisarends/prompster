from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

from agent.playlist import PlaylistDraft, PlaylistDraftUpdate

if TYPE_CHECKING:
    from agent.tools.views import ActionType


class AgentEvent(BaseModel):
    pass


class RunStartedEvent(AgentEvent):
    message: str


class StepStartedEvent(AgentEvent):
    step: int


class AssistantMessageEvent(AgentEvent):
    content: str


class AssistantMessageChunkEvent(AgentEvent):
    chunk: str


class ToolCallEvent(AgentEvent):
    tool_call_id: str
    name: str
    args: dict[str, Any]
    status_label: str | None = None
    action_type: ActionType | None = None


class ToolResultEvent(AgentEvent):
    tool_call_id: str
    name: str
    result: str


class SuspendedForInputEvent(AgentEvent):
    question: str | None = None
    options: list[str] = []
    is_last_question: bool = False


class WorkspaceUpdatedEvent(AgentEvent):
    playlist_draft: PlaylistDraft
    update: PlaylistDraftUpdate


class RunCompletedEvent(AgentEvent):
    output: str
