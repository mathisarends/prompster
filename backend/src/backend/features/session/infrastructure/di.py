from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import AsyncSession

from backend.features.session.application import (
    CreateSessionHandler,
    DeleteSessionHandler,
    GetSessionByIdHandler,
    SearchSpotifyTracksHandler,
    SendMessageHandler,
    UpdateSessionHandler,
)
from backend.features.session.application.ports.spotify_track_search import (
    SpotifyTrackSearch,
)
from backend.features.session.application.ports.title_generator import (
    SessionTitleGenerator,
)
from backend.features.session.domain import SessionRepository
from backend.features.session.infrastructure.spotify_track_search import (
    MockSpotifyTrackSearch,
)
from backend.features.session.infrastructure.title_generator import (
    LLMSessionTitleGenerator,
)
from backend.features.session.infrastructure.orm import SqlSessionRepository
from llmify import ChatOpenAI


class SessionProvider(Provider):
    @provide(scope=Scope.APP)
    def provide_title_generator_llm(self) -> ChatOpenAI:
        return ChatOpenAI()

    @provide(scope=Scope.APP)
    def provide_session_title_generator(
        self,
        llm: ChatOpenAI,
    ) -> SessionTitleGenerator:
        return LLMSessionTitleGenerator(llm=llm)

    @provide(scope=Scope.REQUEST)
    def provide_session_repository(self, session: AsyncSession) -> SessionRepository:
        return SqlSessionRepository(session=session)

    @provide(scope=Scope.REQUEST)
    def provide_create_session_handler(
        self,
        session_repository: SessionRepository,
        title_generator: SessionTitleGenerator,
    ) -> CreateSessionHandler:
        return CreateSessionHandler(
            session_repository=session_repository,
            title_generator=title_generator,
        )

    @provide(scope=Scope.REQUEST)
    def provide_get_session_by_id_handler(
        self,
    ) -> GetSessionByIdHandler:
        return GetSessionByIdHandler()

    @provide(scope=Scope.REQUEST)
    def provide_update_session_handler(
        self,
        session_repository: SessionRepository,
    ) -> UpdateSessionHandler:
        return UpdateSessionHandler(session_repository=session_repository)

    @provide(scope=Scope.REQUEST)
    def provide_send_message_handler(
        self,
        llm: ChatOpenAI,
        session_repository: SessionRepository,
    ) -> SendMessageHandler:
        return SendMessageHandler(
            llm=llm,
            session_repository=session_repository,
        )

    @provide(scope=Scope.REQUEST)
    def provide_delete_session_handler(
        self,
        session_repository: SessionRepository,
    ) -> DeleteSessionHandler:
        return DeleteSessionHandler(session_repository=session_repository)

    @provide(scope=Scope.APP)
    def provide_spotify_track_search(self) -> SpotifyTrackSearch:
        return MockSpotifyTrackSearch()

    @provide(scope=Scope.REQUEST)
    def provide_search_spotify_tracks_handler(
        self,
        spotify_track_search: SpotifyTrackSearch,
    ) -> SearchSpotifyTracksHandler:
        return SearchSpotifyTracksHandler(
            spotify_track_search=spotify_track_search,
        )
