from typing import Any

from pydantic import BaseModel, Field

from agent.deck import DeckDraft, DeckDraftUpdate

from agent.tools.views import ActionResultItem, ActionType, OnboardingSelectionMode


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


class ToolCallSequenceStartedEvent(AgentEvent):
    label: str | None = None


class ToolResultEvent(AgentEvent):
    tool_call_id: str
    name: str
    result: str
    items: list[ActionResultItem] = Field(default_factory=list)


class ToolRetryEvent(AgentEvent):
    """A transient retry of the in-flight tool call's upstream request.

    Surfaced live while the tool is still running so the UI can reassure the
    user (e.g. "Spotify is busy, retrying…") — it does not resolve the call.
    """

    tool_call_id: str
    name: str
    attempt: int
    max_attempts: int
    retry_in_seconds: float | None = None
    status_code: int | None = None


class QuestionAskedEvent(AgentEvent):
    """A question that does not suspend the run — the agent keeps going."""

    question: str | None = None
    hint: str | None = None
    options: list[str] = Field(default_factory=list)
    recommended_option: str | None = None
    selection_mode: OnboardingSelectionMode = OnboardingSelectionMode.SINGLE_SELECT


class SuspendedForUserInputEvent(AgentEvent):
    """The final question — the run suspends and waits for human-in-the-loop input."""

    question: str | None = None
    hint: str | None = None
    options: list[str] = Field(default_factory=list)
    recommended_option: str | None = None
    selection_mode: OnboardingSelectionMode = OnboardingSelectionMode.SINGLE_SELECT
    is_last_question: bool = True


class DeckUpdatedEvent(AgentEvent):
    deck_draft: DeckDraft
    update: DeckDraftUpdate


class RunCompletedEvent(AgentEvent):
    output: str
