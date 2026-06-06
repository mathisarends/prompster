from typing import Any

from pydantic import BaseModel, Field

from agent.playlist import PlaylistDraft, PlaylistDraftUpdate

from agent.tools.views import ActionType, OnboardingSelectionMode

DECIDE_FOR_ME_OPTION = "Entscheide für mich"


def with_decide_for_me_option(options: list[str]) -> list[str]:
    """Return UI-facing onboarding options with the default choice appended."""
    if DECIDE_FOR_ME_OPTION in options:
        return list(options)
    return [*options, DECIDE_FOR_ME_OPTION]


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
    is_onboarding_question: bool = False


class ToolResultEvent(AgentEvent):
    tool_call_id: str
    name: str
    result: str


class QuestionAskedEvent(AgentEvent):
    """A question that does not suspend the run — the agent keeps going."""

    question: str | None = None
    options: list[str] = Field(default_factory=list)
    selection_mode: OnboardingSelectionMode = OnboardingSelectionMode.SINGLE_SELECT


class SuspendedForUserInputEvent(AgentEvent):
    """The final question — the run suspends and waits for human-in-the-loop input."""

    question: str | None = None
    options: list[str] = Field(default_factory=list)
    selection_mode: OnboardingSelectionMode = OnboardingSelectionMode.SINGLE_SELECT
    is_last_question: bool = True


class WorkspaceUpdatedEvent(AgentEvent):
    playlist_draft: PlaylistDraft
    update: PlaylistDraftUpdate


class RunCompletedEvent(AgentEvent):
    output: str
