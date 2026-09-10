import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass
from uuid import UUID, uuid4

from agent import Agent, Spotify
from agent.deck import (
    DeckDraft,
    DeckDraftTrack,
    DeckStore,
)
from agent.tools.views import Phase as AgentPhase
from backend.features.llm.configuration import LLMRegistry
from backend.features.llm.credentials import LLMCredentials
from backend.features.llm.factory import create_openai_llm
from backend.features.session.application.ports import ActiveSessionRunStore
from backend.features.session.application.ports.session_runner import (
    SessionRunner,
    SessionRunnerCancelled,
    SessionRunnerEvent,
)
from backend.features.session.domain import (
    MAX_PLAYLIST_TRACKS,
    Playlist,
    Session,
)
from backend.features.session.infrastructure.agent_event_mapper import (
    AgentSessionEventMapper,
)
from backend.features.session.infrastructure.agent_history import AgentHistoryBuilder
from llmify import ChatModel
from spotifyify import Spotifyify


@dataclass
class _ActiveRun:
    run_id: UUID
    cancellation: asyncio.Event
    agent: Agent

    def stop(self) -> None:
        self.cancellation.set()
        self.agent.request_stop()

    def is_cancelled(self) -> bool:
        return self.cancellation.is_set()


class AgentRuntimeRegistry:
    def __init__(self) -> None:
        self._runs: dict[UUID, _ActiveRun] = {}
        self._lock = asyncio.Lock()

    async def register(self, *, session_id: UUID, run: _ActiveRun) -> None:
        async with self._lock:
            self._runs[session_id] = run

    async def complete(self, *, session_id: UUID, run: _ActiveRun) -> None:
        async with self._lock:
            if self._runs.get(session_id) is run:
                del self._runs[session_id]

    async def stop(self, *, session_id: UUID) -> bool:
        async with self._lock:
            active_run = self._runs.get(session_id)
            if active_run is None:
                return False
            active_run.stop()
            return True


class AgentSessionRunner(SessionRunner):
    def __init__(
        self,
        llm: ChatModel,
        llm_credentials: LLMCredentials,
        spotify: Spotifyify,
        event_mapper: AgentSessionEventMapper,
        history_builder: AgentHistoryBuilder,
        active_runs: ActiveSessionRunStore,
        runtime_registry: AgentRuntimeRegistry,
        llm_registry: LLMRegistry,
        system_prompt: str | None = None,
    ) -> None:
        self._llm = llm
        self._llm_credentials = llm_credentials
        self._spotify = spotify
        self._event_mapper = event_mapper
        self._history_builder = history_builder
        self._active_runs = active_runs
        self._runtime_registry = runtime_registry
        self._llm_registry = llm_registry
        self._system_prompt = system_prompt

    async def run(
        self,
        *,
        session: Session,
        model_id: str | None = None,
    ) -> AsyncIterator[SessionRunnerEvent]:
        agent = await self._create_agent(session=session, model_id=model_id)
        active_run = _ActiveRun(
            run_id=uuid4(),
            cancellation=asyncio.Event(),
            agent=agent,
        )
        try:
            await self._active_runs.register(
                session_id=session.id,
                run_id=active_run.run_id,
            )
            await self._runtime_registry.register(session_id=session.id, run=active_run)
            async for event in agent.stream():
                if await self._is_cancelled(
                    session_id=session.id,
                    active_run=active_run,
                ):
                    yield SessionRunnerCancelled()
                    return
                for session_event in self._event_mapper.map(event):
                    yield session_event
                    if await self._is_cancelled(
                        session_id=session.id,
                        active_run=active_run,
                    ):
                        yield SessionRunnerCancelled()
                        return
        finally:
            await self._runtime_registry.complete(session_id=session.id, run=active_run)
            await self._active_runs.complete(
                session_id=session.id,
                run_id=active_run.run_id,
            )
            await agent.close()

    async def stop(self, *, session_id: UUID) -> bool:
        runtime_stopped = await self._runtime_registry.stop(session_id=session_id)
        persisted = await self._active_runs.request_stop(session_id=session_id)
        return runtime_stopped or persisted

    async def _is_cancelled(
        self,
        *,
        session_id: UUID,
        active_run: _ActiveRun,
    ) -> bool:
        if active_run.is_cancelled():
            return True
        return await self._active_runs.is_stop_requested(
            session_id=session_id,
            run_id=active_run.run_id,
        )

    async def _create_agent(
        self,
        *,
        session: Session,
        model_id: str | None = None,
    ) -> Agent:
        llm = self._llm
        model_info = self._llm_registry.default_model
        if model_id is not None:
            model_info = self._llm_registry.get(model_id)
            llm = create_openai_llm(
                provider_model=model_info.provider_model,
                credentials=self._llm_credentials,
            )

        return Agent(
            llm=llm,
            history=await self._history_builder.build(session=session),
            system_prompt=self._system_prompt,
            spotify=Spotify(client=self._spotify),
            deck_store=_to_deck_store(session.playlist),
            max_deck_tracks=MAX_PLAYLIST_TRACKS,
            max_input_tokens=model_info.input_token_limit,
            phase=_agent_phase_for(session),
        )


def _agent_phase_for(session: Session) -> AgentPhase:
    return AgentPhase(session.phase)


def _to_deck_store(playlist: Playlist | None) -> DeckStore:
    if playlist is None:
        return DeckStore(max_tracks=MAX_PLAYLIST_TRACKS)

    return DeckStore(
        DeckDraft(
            id=playlist.id,
            name=playlist.name or "Deck",
            tracks=[
                DeckDraftTrack(
                    id=track.id,
                    title=track.title,
                    artist=track.artist,
                    year=track.year,
                    spotify_uri=track.spotify_uri,
                    cover_url=track.cover_url,
                )
                for track in playlist.tracks
            ],
        ),
        max_tracks=MAX_PLAYLIST_TRACKS,
    )
