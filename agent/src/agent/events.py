from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from agent.playlist import PlaylistDraft, PlaylistDraftUpdate

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


class QuestionAskedEvent(AgentEvent):
    """A question that does not suspend the run — the agent keeps going."""

    question: str | None = None
    options: list[str] = Field(default_factory=list)


class SuspendedForUserInputEvent(AgentEvent):
    """The final question — the run suspends and waits for human-in-the-loop input."""

    question: str | None = None
    options: list[str] = Field(default_factory=list)
    is_last_question: bool = True


class WorkspaceUpdatedEvent(AgentEvent):
    playlist_draft: PlaylistDraft
    update: PlaylistDraftUpdate


class RunCompletedEvent(AgentEvent):
    output: str
