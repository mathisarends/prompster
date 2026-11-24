from typing import Annotated

from harnessed import Inject, Plugin, SystemPrompt, ToolContext, hook, tool
from harnessed.events import TurnStartedEvent
from harnessed.hooks import Next, PreStep, StepDecision
from harnessed.models import ToolResult
from pydantic import Field

from agent.onboarding.events import QuestionAskedEvent, SelectionMode


class OnboardingPlugin(Plugin):
    """Ask the user clarifying questions, then end the turn until they answered."""

    events = (QuestionAskedEvent,)

    def __init__(self) -> None:
        super().__init__()
        self._waiting_for_answers = False

    def instructions(self) -> SystemPrompt:
        return SystemPrompt(_INSTRUCTIONS)

    @tool
    async def ask_onboarding_question(
        self,
        *,
        question: Annotated[str, Field(description="The question shown to the user.")],
        options: Annotated[
            list[str],
            Field(
                min_length=2,
                max_length=4,
                description="2-4 tag-style answers of about three words each.",
            ),
        ],
        hint: Annotated[
            str | None,
            Field(
                description="Optional short note below the question: a tip or a warning."
            ),
        ] = None,
        selection_mode: Annotated[
            SelectionMode,
            Field(
                description="single_select for one answer, multi_select for several."
            ),
        ] = SelectionMode.SINGLE_SELECT,
        recommended_option: Annotated[
            str | None,
            Field(description="Your recommendation, copied verbatim from options."),
        ] = None,
        is_last_question: Annotated[
            bool,
            Field(description="True only on the final question of this onboarding."),
        ] = False,
        ctx: Inject[ToolContext],
    ) -> ToolResult:
        """Ask the user one onboarding question with short answer options."""
        await ctx.emit(
            QuestionAskedEvent(
                question=question,
                options=tuple(options),
                hint=hint,
                recommended_option=recommended_option,
                selection_mode=selection_mode,
                is_last_question=is_last_question,
            )
        )
        result = f"Frage gestellt: {question}"
        if not is_last_question:
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


_INSTRUCTIONS = """\
<onboarding>
You are in onboarding. Gather what you need to build a great deck, then stop. The app moves to the build phase once the user has answered.

How a turn works:
1. Write one or two sentences reacting to the deck idea and say you have a few questions.
2. In that same response, call `ask_onboarding_question` 3 to 5 times in a row, with no text between the calls. Do not wait for answers between questions.
3. Set `is_last_question=true` on the final call only.

Choosing questions:
- Tailor them to the request. Never ask for something the user already told you.
- Always include one question about difficulty or how well-known the songs should be.
- Useful angles: occasion and audience, eras, mood, genre breadth, must-have artists, no-gos.
- Never ask how many songs or cards the deck should have.
- Ask about time as broad spans ("Frühe 2000er bis heute", "90er bis 2010er", "Alle Jahrzehnte"), not as single years or long decade checklists.
- If the request is very specific, mention in your opening that a little breadth often helps, then use one question and its `hint` to ask whether adjacent artists, neighboring scenes, or a wider time span are welcome. Skip this if the user already ruled it out.

Writing options:
- Offer 3 options, 4 at most, each a genuinely different direction.
- Keep each to about three words, as a scannable tag: "Nur Superhits", not a sentence.
- Do not add "Sonstiges". The UI already has a free-text answer.
- Always set `recommended_option` to one option, copied verbatim.
- Use `multi_select` only when several answers make sense together, such as genres, decades, or no-gos.

Do not research, suggest a finished track list, or build anything during onboarding.
</onboarding>"""
