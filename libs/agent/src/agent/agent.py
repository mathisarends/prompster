from collections.abc import AsyncGenerator, Sequence
from contextlib import AsyncExitStack
from enum import StrEnum
from pathlib import Path
from typing import Self

import harnessed
from harnessed import (
    AgentLoop,
    Compaction,
    Context,
    FinalStepPolicy,
    Plugin,
    SessionStatus,
)
from harnessed import Session as HarnessedSession
from harnessed.models import ToolCall, UserMessage
from harnessed.models.pydantic_ai import PydanticAIModel
from harnessed.prompts import SystemPrompt
from harnessed.sessions import SessionCommit
from pydantic_ai.models import Model

from agent.activity import tool_activity
from agent.conversation import (
    AgentCheckpoint,
    AgentCommit,
    CommitSink,
    InputImage,
    ProviderReplayGuard,
    ReplyPlugin,
    UserEvent,
    user_input,
)
from agent.deck import Deck, DeckPlugin, DeckStore
from agent.events import AGENT_EVENT_TYPES, AgentEvent
from agent.onboarding import OnboardingPlugin
from agent.prompts import read_prompt
from agent.research import ResearchPlugin, Spotify
from agent.review import ReviewPlugin


class Phase(StrEnum):
    ONBOARDING = "onboarding"
    BUILD = "build"


class Agent:
    """Prompster's deck-building agent: one live harnessed session.

    Open it with ``async with``. It continues ``checkpoint`` when given and
    hands every durable change to ``on_commit``, so a stored checkpoint reopens
    the agent exactly where it stopped. ``stream`` runs one turn and yields its
    events; ``pause``, ``resume``, ``stop`` and ``abort`` control the turn from
    anywhere else while it runs.
    """

    def __init__(
        self,
        llm: Model,
        *,
        phase: Phase = Phase.ONBOARDING,
        deck: Deck | None = None,
        spotify: Spotify | None = None,
        max_deck_tracks: int = 50,
        max_input_tokens: int | None = None,
        compaction_threshold: float = 0.8,
        checkpoint: AgentCheckpoint | None = None,
        on_commit: CommitSink | None = None,
        session_id: str | None = None,
        transcript: str | None = None,
    ) -> None:
        self._phase = phase
        self._store = DeckStore(deck, max_tracks=max_deck_tracks)
        self._spotify = spotify if spotify is not None else Spotify()
        self._checkpoint = checkpoint
        self._on_commit = on_commit
        self._session_id = session_id
        self._transcript = transcript
        self._harness = harnessed.Agent(
            model=PydanticAIModel(
                llm,
                context_window=(
                    max_input_tokens
                    if max_input_tokens is not None
                    else _DEFAULT_CONTEXT_WINDOW
                ),
            ),
            instructions=SystemPrompt.from_plugins(read_prompt(_INSTRUCTIONS)),
            plugins=self._plugins(),
            context=Context(
                max_tool_output_chars=_MAX_TOOL_OUTPUT_CHARS,
                compaction=Compaction(
                    at=compaction_threshold,
                    prompt=read_prompt(_COMPACTION_PROMPT),
                    keep_last_steps=_COMPACTION_KEEP_LAST_STEPS,
                ),
            ),
            loop=AgentLoop(
                max_steps=_MAX_STEPS[phase],
                tool_timeout_seconds=_TOOL_TIMEOUT_SECONDS,
                max_parallel_tools=_MAX_PARALLEL_TOOLS,
                final_step=FinalStepPolicy.SUMMARIZE,
                error_formatter=_format_tool_error,
            ),
        )
        self._exit_stack = AsyncExitStack()
        self._session: HarnessedSession | None = None

    async def __aenter__(self) -> Self:
        try:
            await self._open()
        except BaseException:
            await self.__aexit__()
            raise
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        self._session = None
        await self._exit_stack.aclose()

    @property
    def phase(self) -> Phase:
        return self._phase

    @property
    def deck(self) -> Deck | None:
        return self._store.deck

    @property
    def status(self) -> SessionStatus:
        return self._live.status

    async def stream(
        self,
        text: str = "",
        *,
        images: Sequence[InputImage] = (),
        curation_events: Sequence[UserEvent] = (),
    ) -> AsyncGenerator[AgentEvent]:
        message = user_input(text, images=images, curation_events=curation_events)
        async with self._live.stream(message, buffer_size=_STREAM_BUFFER_SIZE) as run:
            async for item in run:
                if isinstance(item, AGENT_EVENT_TYPES):
                    yield item

    async def pause(self) -> None:
        """Pause after the current step; the stream reports the new status."""
        await self._live.pause()

    async def resume(self) -> None:
        await self._live.resume()

    async def stop(self) -> None:
        """Finish the current step, then end the turn."""
        await self._live.stop()

    async def abort(self) -> None:
        """End the turn now, cancelling a running model request or tool."""
        await self._live.abort()

    @property
    def _live(self) -> HarnessedSession:
        if self._session is None:
            raise RuntimeError("Open the agent with 'async with' first.")
        return self._session

    async def _open(self) -> None:
        stack = self._exit_stack
        await stack.enter_async_context(self._spotify)
        self._session = session = await stack.enter_async_context(
            self._harness.session(
                state=self._checkpoint.restore() if self._checkpoint else None,
                id=self._session_id,
                on_commit=self._commit if self._on_commit is not None else None,
            )
        )
        if session.status is SessionStatus.PAUSED:
            # The process ended while paused. The user writes again, so the open
            # turn ends here and the new message starts a fresh one.
            await session.stop()
        elif self._checkpoint is None and self._transcript:
            await session.append_message(UserMessage(self._transcript))

    async def _commit(self, commit: SessionCommit) -> None:
        if self._on_commit is not None and commit.session_id == self._live.id:
            await self._on_commit(AgentCommit.from_session(commit))

    def _plugins(self) -> list[Plugin]:
        if self._phase is Phase.ONBOARDING:
            capabilities: list[Plugin] = [OnboardingPlugin()]
        else:
            capabilities = [
                *tool_activity(),
                ResearchPlugin(self._spotify),
                DeckPlugin(self._store),
                ReviewPlugin(self._store),
            ]
        # Hooks run in mount order: the deck settles before the final reply.
        return [*capabilities, ProviderReplayGuard(), ReplyPlugin()]


_PACKAGE = Path(__file__).parent
_INSTRUCTIONS = _PACKAGE / "instructions.md"
_COMPACTION_PROMPT = _PACKAGE / "conversation" / "compaction.md"
_COMPACTION_KEEP_LAST_STEPS = 3
_DEFAULT_CONTEXT_WINDOW = 272_000
_MAX_STEPS = {Phase.ONBOARDING: 6, Phase.BUILD: 48}
_TOOL_TIMEOUT_SECONDS = 90.0
_MAX_PARALLEL_TOOLS = 4
_MAX_TOOL_OUTPUT_CHARS = 24_000
# Deck changes, previews and deltas of a long turn must not block the loop
# while the consumer forwards them to a websocket.
_STREAM_BUFFER_SIZE = 1024


def _format_tool_error(_call: ToolCall, error: Exception) -> str:
    # The model reads tool errors and can retry or choose another tool.
    return f"Error: {error}"
