from harnessed import Plugin, SystemPrompt, hook, tool
from harnessed.hooks import Next, PreStep, StepDecision
from harnessed.models import ToolResult

from agent.events import QuestionAskedEvent, SuspendedForUserInputEvent
from agent.messages import load_prompt
from agent.plugins.run_context import AgentRunContext
from agent.tools.params import AskOnboardingQuestionParams


class OnboardingPlugin(Plugin):
    """Ask the user clarifying questions, then suspend until they answered."""

    def __init__(self, run: AgentRunContext) -> None:
        super().__init__()
        self._run = run

    def instructions(self) -> SystemPrompt:
        return SystemPrompt(load_prompt("onboarding"))

    @tool(
        description="Ask the user one onboarding question with short answer options.",
        params=AskOnboardingQuestionParams,
    )
    async def ask_onboarding_question(
        self,
        params: AskOnboardingQuestionParams,
    ) -> ToolResult:
        question = {
            "question": params.question,
            "hint": params.hint,
            "options": list(params.options),
            "recommended_option": params.recommended_option,
            "selection_mode": params.selection_mode,
        }
        result = f"Frage gestellt: {params.question}"
        if params.is_last_question:
            self._run.suspended = True
            self._run.channel.publish(SuspendedForUserInputEvent(**question))
            return ToolResult(result, break_chain=True)
        self._run.channel.publish(QuestionAskedEvent(**question))
        return ToolResult(result)

    @hook(PreStep)
    async def end_turn_when_suspended(
        self,
        _event: PreStep,
        next_: Next[StepDecision],
    ) -> StepDecision:
        if self._run.suspended:
            return StepDecision.reject()
        return await next_()
