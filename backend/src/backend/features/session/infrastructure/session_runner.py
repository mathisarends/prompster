import asyncio
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import aclosing
from uuid import UUID, uuid4

from agent import Agent, AgentCommit, Deck, DeckTrack, Spotify
from agent import Phase as AgentPhase
from harnessed.events import TextDeltaEvent
from pydantic_ai.models import Model
from spotifyify import SpotifyClient

from backend.features.llm.application import ChatModels
from backend.features.llm.domain import LLMRegistry
from backend.features.session.application.ports import (
    ActiveSessionRunStore,
    SessionRunner,
    SessionRunnerEvent,
)
from backend.features.session.domain import MAX_PLAYLIST_TRACKS, Playlist, Session
from backend.features.session.infrastructure.agent_checkpoint_store import (
    SqlAgentCheckpointStore,
)
from backend.features.session.infrastructure.agent_event_mapper import (
    AgentRunEventMapper,
)
from backend.features.session.infrastructure.agent_input import AgentInputBuilder


class AgentRuntimeRegistry:
    """The agents running in this process, so requests can control their turn.

    A pause waits for the current step to end, so it runs in the background;
    the stream reports when the turn is paused.
    """

    def __init__(self) -> None:
        self._agents: dict[UUID, Agent] = {}
        self._controls: set[asyncio.Task[None]] = set()

    def register(self, *, session_id: UUID, agent: Agent) -> None:
        self._agents[session_id] = agent

    def complete(self, *, session_id: UUID, agent: Agent) -> None:
        if self._agents.get(session_id) is agent:
            del self._agents[session_id]

    def abort(self, *, session_id: UUID) -> bool:
        return self._control(session_id, Agent.abort)

    def pause(self, *, session_id: UUID) -> bool:
        return self._control(session_id, Agent.pause)

    def resume(self, *, session_id: UUID) -> bool:
        return self._control(session_id, Agent.resume)

    def _control(
        self, session_id: UUID, action: Callable[[Agent], Awaitable[None]]
    ) -> bool:
        agent = self._agents.get(session_id)
        if agent is None:
            return False
        task = asyncio.create_task(action(agent))
        self._controls.add(task)
        task.add_done_callback(self._controls.discard)
        return True


class AgentSessionRunner(SessionRunner):
    """Runs the agent on its stored checkpoint and saves every commit back."""

    def __init__(
        self,
        llm: Model,
        chat_models: ChatModels,
        spotify: SpotifyClient,
        input_builder: AgentInputBuilder,
        checkpoints: SqlAgentCheckpointStore,
        active_runs: ActiveSessionRunStore,
        runtime_registry: AgentRuntimeRegistry,
        llm_registry: LLMRegistry,
    ) -> None:
        self._llm = llm
        self._chat_models = chat_models
        self._spotify = spotify
        self._input_builder = input_builder
        self._checkpoints = checkpoints
        self._active_runs = active_runs
        self._runtime_registry = runtime_registry
        self._llm_registry = llm_registry

    async def run(
        self,
        *,
        session: Session,
        model_id: str | None = None,
    ) -> AsyncGenerator[SessionRunnerEvent]:
        agent_input = await self._input_builder.build(session=session)
        agent = await self._create_agent(
            session=session, model_id=model_id, transcript=agent_input.transcript
        )
        mapper = AgentRunEventMapper()
        run_id = uuid4()
        async with agent:
            await self._active_runs.register(session_id=session.id, run_id=run_id)
            self._runtime_registry.register(session_id=session.id, agent=agent)
            try:
                stream = agent.stream(
                    agent_input.text,
                    images=agent_input.images,
                    curation_events=agent_input.curation_events,
                )
                aborting = False
                async with aclosing(stream) as events:
                    async for event in events:
                        for runner_event in mapper.map(event):
                            yield runner_event
                        if not aborting and not isinstance(event, TextDeltaEvent):
                            aborting = await self._abort_if_stop_requested(
                                agent=agent, session_id=session.id, run_id=run_id
                            )
            finally:
                self._runtime_registry.complete(session_id=session.id, agent=agent)
                await self._active_runs.complete(session_id=session.id, run_id=run_id)

    async def stop(self, *, session_id: UUID) -> bool:
        aborted = self._runtime_registry.abort(session_id=session_id)
        persisted = await self._active_runs.request_stop(session_id=session_id)
        return aborted or persisted

    async def pause(self, *, session_id: UUID) -> bool:
        return self._runtime_registry.pause(session_id=session_id)

    async def resume(self, *, session_id: UUID) -> bool:
        return self._runtime_registry.resume(session_id=session_id)

    async def _abort_if_stop_requested(
        self, *, agent: Agent, session_id: UUID, run_id: UUID
    ) -> bool:
        # Another process may own the stop request; the turn result then
        # reports the cancellation like a local stop.
        if not await self._active_runs.is_stop_requested(
            session_id=session_id, run_id=run_id
        ):
            return False
        await agent.abort()
        return True

    async def _create_agent(
        self,
        *,
        session: Session,
        model_id: str | None,
        transcript: str | None,
    ) -> Agent:
        llm = self._llm
        model_info = self._llm_registry.default_model
        if model_id is not None:
            model_info = self._llm_registry.get(model_id)
            llm = self._chat_models.get(model_info)

        checkpoint = await self._checkpoints.load(session_id=session.id)

        async def save(commit: AgentCommit) -> None:
            await self._checkpoints.save(session_id=session.id, commit=commit)

        return Agent(
            llm,
            phase=AgentPhase(session.phase),
            deck=_to_deck(session.playlist),
            spotify=Spotify(client=self._spotify),
            max_deck_tracks=MAX_PLAYLIST_TRACKS,
            max_input_tokens=model_info.input_token_limit,
            checkpoint=checkpoint,
            on_commit=save,
            session_id=str(session.id),
            transcript=transcript,
        )


def _to_deck(playlist: Playlist | None) -> Deck | None:
    if playlist is None:
        return None
    return Deck(
        id=str(playlist.id),
        name=playlist.name or "Deck",
        tracks=tuple(
            DeckTrack(
                id=str(track.id),
                title=track.title,
                artist=track.artist,
                year=track.year,
                spotify_uri=track.spotify_uri,
                cover_url=track.cover_url,
            )
            for track in playlist.tracks
        ),
    )
