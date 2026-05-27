from collections.abc import AsyncIterator

from agent.agent import Agent
from agent import Spotify
from agent.playlist import (
    PlaylistDraft,
    PlaylistDraftTrack,
    PlaylistDraftStore,
)

from llmify import ChatModel
from spotifyify import Spotifyify

from backend.features.session.application.ports.session_runner import (
    SessionRunner,
    SessionRunnerEvent,
)
from backend.features.session.domain import Playlist, Session
from backend.features.session.infrastructure.agent_event_mapper import (
    AgentSessionEventMapper,
)
from backend.features.session.infrastructure.agent_history import AgentHistoryBuilder


class AgentSessionRunner(SessionRunner):
    def __init__(
        self,
        llm: ChatModel,
        spotify: Spotifyify,
        event_mapper: AgentSessionEventMapper | None = None,
        history_builder: AgentHistoryBuilder | None = None,
        system_prompt: str | None = None,
    ) -> None:
        self._llm = llm
        self._spotify = spotify
        self._event_mapper = event_mapper or AgentSessionEventMapper()
        self._history_builder = history_builder or AgentHistoryBuilder()
        self._system_prompt = system_prompt

    async def run(self, *, session: Session) -> AsyncIterator[SessionRunnerEvent]:
        agent = self._create_agent(session=session)
        try:
            async for event in agent.stream():
                for session_event in self._event_mapper.map(event):
                    yield session_event
        finally:
            await agent.close()

    def _create_agent(self, *, session: Session) -> Agent:
        return Agent(
            llm=self._llm,
            history=self._history_builder.build(session=session),
            system_prompt=self._system_prompt,
            spotify=Spotify(client=self._spotify),
            playlist_store=_to_playlist_draft_store(session.playlist),
        )


def _to_playlist_draft_store(playlist: Playlist | None) -> PlaylistDraftStore:
    if playlist is None:
        return PlaylistDraftStore()

    return PlaylistDraftStore(
        PlaylistDraft(
            id=playlist.id,
            name=playlist.name or "Playlist",
            tracks=[
                PlaylistDraftTrack(
                    id=track.id,
                    title=track.title,
                    artist=track.artist,
                    year=track.year,
                    spotify_uri=track.spotify_uri,
                    cover_url=track.cover_url,
                    is_pinned=track.is_pinned,
                )
                for track in playlist.tracks
            ],
        )
    )
