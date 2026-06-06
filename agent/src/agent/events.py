from typing import Any

from pydantic import BaseModel, Field

from agent.deck import DeckDraft, DeckDraftUpdate

from agent.tools.views import ActionType, OnboardingSelectionMode


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
    hint: str | None = None
    options: list[str] = Field(default_factory=list)
    selection_mode: OnboardingSelectionMode = OnboardingSelectionMode.SINGLE_SELECT


class SuspendedForUserInputEvent(AgentEvent):
    """The final question — the run suspends and waits for human-in-the-loop input."""

    question: str | None = None
    hint: str | None = None
    options: list[str] = Field(default_factory=list)
    selection_mode: OnboardingSelectionMode = OnboardingSelectionMode.SINGLE_SELECT
    is_last_question: bool = True


class DeckUpdatedEvent(AgentEvent):
    deck_draft: DeckDraft
    update: DeckDraftUpdate


class RunCompletedEvent(AgentEvent):
    output: str
