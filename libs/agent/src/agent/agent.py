import asyncio
from collections.abc import AsyncGenerator, Sequence

from harnessed import Agent as HarnessedAgent
from harnessed import AgentLoop, Compaction, Context, Plugin, SystemPrompt
from harnessed.events.turn import FinalStepPolicy
from harnessed.models import Message, ToolCall
from harnessed.models.pydantic_ai import PydanticAIModel
from harnessed.plugins import CallEnvelope, EnvelopePosition, InvalidEnvelope
from harnessed.runtime.session import Session
from pydantic_ai.models import Model

from agent.deck import DeckStore
from agent.events import AgentEvent, RunCompletedEvent, RunStartedEvent
from agent.messages import load_prompt, render_user_message_content, replay_history
from agent.plugins import (
    AgentRunContext,
    DeckPlugin,
    EventBridge,
    OnboardingPlugin,
    ResearchPlugin,
    ReviewPlugin,
    SequenceLabel,
    StatusLabel,
    needs_status_label,
)
from agent.tools import DeckCritic, Spotify
from agent.views import Phase, UserEvent

_DEFAULT_INPUT_TOKEN_LIMIT = 272_000
_ONBOARDING_MAX_STEPS = 6
_BUILD_MAX_STEPS = 48
_TOOL_TIMEOUT_SECONDS = 90.0
_MAX_PARALLEL_TOOLS = 4
_MAX_TOOL_OUTPUT_CHARS = 24_000


class Agent:
    """Prompster's deck-building agent, running on a harnessed session per run."""

    def __init__(
        self,
        llm: Model,
        history: Sequence[Message] | None = None,
        system_prompt: str | None = None,
        spotify: Spotify | None = None,
        deck_store: DeckStore | None = None,
        max_deck_tracks: int = 50,
        phase: Phase = Phase.ONBOARDING,
        max_input_tokens: int | None = None,
        compaction_threshold: float = 0.8,
    ) -> None:
        self._history = list(history) if history is not None else []
        self._system_prompt = system_prompt
        self._spotify = spotify if spotify is not None else Spotify()
        self._deck_store = (
            deck_store if deck_store is not None else DeckStore(max_tracks=max_deck_tracks)
        )
        self._max_deck_tracks = max_deck_tracks
        self._phase = phase
        self._model = PydanticAIModel(
            llm,
            context_window=(
                max_input_tokens
                if max_input_tokens is not None
                else _DEFAULT_INPUT_TOKEN_LIMIT
            ),
        )
        self._compaction_threshold = compaction_threshold
        self._critic = DeckCritic(
            llm,
            deck_store=self._deck_store,
            target_size=max_deck_tracks,
        )
        self._stop_requested = asyncio.Event()

    @property
    def phase(self) -> Phase:
        return self._phase

    async def close(self) -> None:
        await self._spotify.close()

    def request_stop(self) -> None:
        self._stop_requested.set()

    async def stream(
        self,
        message: str | None = None,
        curation_events: Sequence[UserEvent] | None = None,
    ) -> AsyncGenerator[AgentEvent, None]:
        self._stop_requested.clear()
        new_input = None
        if message is not None or curation_events:
            text = message if message is not None else ""
            new_input = render_user_message_content(text, curation_events)
            yield RunStartedEvent(message=text)

        replay = replay_history(self._history, new_input=new_input)
        run = AgentRunContext(
            spotify=self._spotify,
            deck_store=self._deck_store,
            critic=self._critic,
            max_deck_tracks=self._max_deck_tracks,
        )
        harness = self._build_harness(run)
        async with harness.session(state=replay.state) as session:
            handle = await session.submit(replay.run_input)
            stop_watcher = asyncio.create_task(self._abort_when_stopped(session))

            async def finish() -> str:
                try:
                    result = await handle.result()
                    return result.text
                finally:
                    run.channel.close()

            completion = asyncio.create_task(finish())
            try:
                async for event in run.channel:
                    yield event
                output = await completion
            finally:
                stop_watcher.cancel()
                completion.cancel()
                await asyncio.gather(stop_watcher, completion, return_exceptions=True)

        if not run.suspended and not self._stop_requested.is_set():
            yield RunCompletedEvent(output=output)

    async def _abort_when_stopped(self, session: Session) -> None:
        await self._stop_requested.wait()
        await session.abort()

    def _build_harness(self, run: AgentRunContext) -> HarnessedAgent:
        is_onboarding = self._phase == Phase.ONBOARDING
        return HarnessedAgent(
            model=self._model,
            instructions=self._build_instructions(),
            plugins=[
                *(_onboarding_plugins(run) if is_onboarding else _build_plugins(run)),
                EventBridge(run, compaction_threshold=self._compaction_threshold),
            ],
            context=Context(
                max_tool_output_chars=_MAX_TOOL_OUTPUT_CHARS,
                compaction=Compaction(
                    at=self._compaction_threshold,
                    prompt=load_prompt("compaction"),
                    keep_last_steps=3,
                ),
            ),
            loop=AgentLoop(
                max_steps=_ONBOARDING_MAX_STEPS if is_onboarding else _BUILD_MAX_STEPS,
                tool_timeout_seconds=_TOOL_TIMEOUT_SECONDS,
                max_parallel_tools=_MAX_PARALLEL_TOOLS,
                final_step=FinalStepPolicy.SUMMARIZE,
                error_formatter=_format_tool_error,
            ),
        )

    def _build_instructions(self) -> SystemPrompt:
        if self._system_prompt:
            return SystemPrompt(self._system_prompt)
        return SystemPrompt.from_plugins(load_prompt("shared"))


def _onboarding_plugins(run: AgentRunContext) -> list[Plugin]:
    return [OnboardingPlugin(run)]


def _build_plugins(run: AgentRunContext) -> list[Plugin]:
    return [
        CallEnvelope(
            StatusLabel,
            select=needs_status_label,
            on_invalid=InvalidEnvelope.DROP,
            position=EnvelopePosition.TRAILING,
            name="status-label",
        ),
        CallEnvelope(
            SequenceLabel,
            on_invalid=InvalidEnvelope.DROP,
            position=EnvelopePosition.TRAILING,
            name="sequence-label",
        ),
        ResearchPlugin(run),
        DeckPlugin(run),
        ReviewPlugin(run),
    ]


def _format_tool_error(_call: ToolCall, error: Exception) -> str:
    # The model reads tool errors and can retry or choose another tool.
    return f"Error: {error}"
