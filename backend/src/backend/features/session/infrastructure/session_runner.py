import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass
from uuid import UUID

from agent import Agent
from agent import Spotify
from agent.deck import (
    DeckDraft,
    DeckDraftTrack,
    DeckStore,
)
from agent.tools.views import Phase as AgentPhase

from backend.features.session.domain import MAX_PLAYLIST_TRACKS
from llmify import ChatModel
from spotifyify import Spotifyify

from backend.features.session.application.ports.session_runner import (
    SessionRunner,
    SessionRunnerCancelled,
    SessionRunnerEvent,
)
from backend.features.session.domain import (
    Playlist,
    Session,
)
from backend.features.session.infrastructure.agent_event_mapper import (
    AgentSessionEventMapper,
)
from backend.features.session.infrastructure.agent_history import AgentHistoryBuilder


@dataclass
class _ActiveRun:
    cancellation: asyncio.Event
    agent: Agent

    def stop(self) -> None:
        self.cancellation.set()
        self.agent.request_stop()

    def is_cancelled(self) -> bool:
        return self.cancellation.is_set()


class _ActiveRunRegistry:
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
        spotify: Spotifyify,
        event_mapper: AgentSessionEventMapper,
        history_builder: AgentHistoryBuilder,
        system_prompt: str | None = None,
    ) -> None:
        self._llm = llm
        self._spotify = spotify
        self._event_mapper = event_mapper
        self._history_builder = history_builder
        self._system_prompt = system_prompt
        self._active_runs = _ActiveRunRegistry()

    async def run(self, *, session: Session) -> AsyncIterator[SessionRunnerEvent]:
        agent = self._create_agent(session=session)
        active_run = _ActiveRun(cancellation=asyncio.Event(), agent=agent)
        await self._active_runs.register(session_id=session.id, run=active_run)
        try:
            async for event in agent.stream():
                if active_run.is_cancelled():
                    yield SessionRunnerCancelled()
                    return
                for session_event in self._event_mapper.map(event):
                    yield session_event
                    if active_run.is_cancelled():
                        yield SessionRunnerCancelled()
                        return
        finally:
            await self._active_runs.complete(session_id=session.id, run=active_run)
            await agent.close()

    async def stop(self, *, session_id: UUID) -> bool:
        return await self._active_runs.stop(session_id=session_id)

    def _create_agent(self, *, session: Session) -> Agent:
        return Agent(
            llm=self._llm,
            history=self._history_builder.build(session=session),
            system_prompt=self._system_prompt,
            spotify=Spotify(client=self._spotify),
            deck_store=_to_deck_store(session.playlist),
            max_deck_tracks=MAX_PLAYLIST_TRACKS,
            phase=_agent_phase_for(session),
        )


def _agent_phase_for(session: Session) -> AgentPhase:
    return AgentPhase(session.phase)


def _to_deck_store(playlist: Playlist | None) -> DeckStore:
    if playlist is None:
        return DeckStore()

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
        )
    )
