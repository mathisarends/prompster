from pathlib import Path

from harnessed import Inject, Plugin, SystemPrompt, ToolContext, hook, tool
from harnessed.events import TurnStartedEvent
from harnessed.hooks import Next, PreStep, StepDecision
from harnessed.models import ToolResult

from agent.onboarding.events import QuestionAskedEvent
from agent.onboarding.params import AskOnboardingQuestionParams
from agent.prompts import read_prompt


class OnboardingPlugin(Plugin):
    """Ask the user clarifying questions, then end the turn until they answered."""

    events = (QuestionAskedEvent,)

    def __init__(self) -> None:
        super().__init__()
        self._waiting_for_answers = False

    def instructions(self) -> SystemPrompt:
        return SystemPrompt(read_prompt(Path(__file__).with_name("prompt.md")))

    @tool(
        description="Ask the user one onboarding question with short answer options.",
        params=AskOnboardingQuestionParams,
    )
    async def ask_onboarding_question(
        self,
        params: AskOnboardingQuestionParams,
        *,
        ctx: Inject[ToolContext],
    ) -> ToolResult:
        await ctx.emit(
            QuestionAskedEvent(
                question=params.question,
                options=tuple(params.options),
                hint=params.hint,
                recommended_option=params.recommended_option,
                selection_mode=params.selection_mode,
                is_last_question=params.is_last_question,
            )
        )
        result = f"Frage gestellt: {params.question}"
        if not params.is_last_question:
            return ToolResult(result)
        self._waiting_for_answers = True
        return ToolResult(result, break_chain=True)

    @hook(TurnStartedEvent)
    def start_asking(self, _event: TurnStartedEvent) -> None:
        self._waiting_for_answers = False

    @hook(PreStep)
    async def wait_for_answers(
        self,
        _event: PreStep,
        next_: Next[StepDecision],
    ) -> StepDecision:
        if self._waiting_for_answers:
            return StepDecision.reject()
        return await next_()
