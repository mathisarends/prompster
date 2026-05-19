from collections.abc import AsyncGenerator

from dishka import Provider, Scope, provide
from llmify import ChatOpenAI
from sqlalchemy.ext.asyncio import AsyncSession
from spotifyify import SpotifyCredentials, Spotifyify
from spotifyify.cache_handler import MemoryCacheHandler

from backend.env import LLMCredentials
from backend.features.session.infrastructure.repository import SqlSessionRepository

from backend.features.session.application import (
    SearchSpotifyTracksHandler,
    SessionService,
)
from backend.features.session.application.ports.session_runner import SessionRunner
from backend.features.session.application.ports.session_summary_query import (
    SessionSummaryQuery,
)
from backend.features.session.application.ports.spotify_track_search import (
    SpotifyTrackSearch,
)
from backend.features.session.application.ports.title_generator import (
    SessionTitleGenerator,
)
from backend.features.session.domain import SessionRepository
from backend.features.session.infrastructure.session_runner import LLMSessionRunner
from backend.features.session.infrastructure.spotify_track_search import (
    SpotifyifyTrackSearch,
)
from backend.features.session.infrastructure.session_summary_query import (
    SqlSessionSummaryQuery,
)
from backend.features.session.infrastructure.title_generator import (
    LLMSessionTitleGenerator,
)


class SessionProvider(Provider):
    @provide(scope=Scope.APP)
    def provide_title_generator_llm(self) -> ChatOpenAI:
        credentials = self.llm_credentials()
        return ChatOpenAI(api_key=credentials.openai_api_key)

    @provide(scope=Scope.APP)
    def llm_credentials(self) -> LLMCredentials:
        return LLMCredentials()

    @provide(scope=Scope.APP)
    def provide_session_title_generator(
        self,
        llm: ChatOpenAI,
    ) -> SessionTitleGenerator:
        return LLMSessionTitleGenerator(llm=llm)

    @provide(scope=Scope.APP)
    def provide_session_runner(self, llm: ChatOpenAI) -> SessionRunner:
        return LLMSessionRunner(llm=llm, system_prompt="You are a helpful assistant.")

    @provide(scope=Scope.REQUEST)
    def provide_session_repository(self, session: AsyncSession) -> SessionRepository:
        return SqlSessionRepository(session=session)

    @provide(scope=Scope.REQUEST)
    def provide_session_summary_query(
        self,
        session: AsyncSession,
    ) -> SessionSummaryQuery:
        return SqlSessionSummaryQuery(session=session)

    @provide(scope=Scope.REQUEST)
    def provide_session_service(
        self,
        session_repository: SessionRepository,
        session_summary_query: SessionSummaryQuery,
        title_generator: SessionTitleGenerator,
        runner: SessionRunner,
    ) -> SessionService:
        return SessionService(
            session_repository=session_repository,
            session_summary_query=session_summary_query,
            title_generator=title_generator,
            runner=runner,
        )

    @provide(scope=Scope.APP)
    def spotify_credentials(self) -> SpotifyCredentials:
        return SpotifyCredentials()

    @provide(scope=Scope.APP)
    async def spotify(
        self,
        credentials: SpotifyCredentials,
    ) -> AsyncGenerator[Spotifyify, None]:
        spotify = Spotifyify(
            credentials=credentials,
            cache_handler=MemoryCacheHandler(),
        )
        try:
            yield spotify
        finally:
            await spotify.close()

    @provide(scope=Scope.APP)
    def provide_spotify_track_search(self, spotify: Spotifyify) -> SpotifyTrackSearch:
        return SpotifyifyTrackSearch(spotify=spotify)

    @provide(scope=Scope.REQUEST)
    def provide_search_spotify_tracks_handler(
        self,
        spotify_track_search: SpotifyTrackSearch,
    ) -> SearchSpotifyTracksHandler:
        return SearchSpotifyTracksHandler(
            spotify_track_search=spotify_track_search,
        )
