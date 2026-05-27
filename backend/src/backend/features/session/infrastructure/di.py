from dishka import Provider, Scope, provide
from llm import LLMCredentials, create_gpt_5_4
from llmify import ChatModel
from sqlalchemy.ext.asyncio import AsyncSession
from spotifyify import Spotifyify

from backend.features.oauth_connections.application import SpotifyTokenService
from backend.features.session.infrastructure.repository import SqlSessionRepository
from backend.features.spotify.infrastructure.spotify_service import SpotifyService

from backend.features.session.application import (
    SessionPlaylistExporter,
    SessionConversationService,
    SessionService,
    SessionSpotifyPlaylistExporter,
)
from backend.features.session.application.ports import (
    PlaylistDeckGenerator,
    PlaylistMetadataGenerator,
)
from backend.features.session.application.ports.session_runner import SessionRunner
from backend.features.session.application.ports.session_summary_query import (
    SessionSummaryQuery,
)
from backend.features.session.application.ports.title_generator import (
    SessionTitleGenerator,
)
from backend.features.session.domain import SessionRepository
from backend.features.session.infrastructure.agent_event_mapper import (
    AgentSessionEventMapper,
)
from backend.features.session.infrastructure.agent_history import AgentHistoryBuilder
from backend.features.session.infrastructure.session_runner import AgentSessionRunner
from backend.features.session.infrastructure.pdf_generator import (
    TypstPlaylistDeckGenerator,
)
from backend.features.session.infrastructure.playlist_metadata_generator import (
    LLMPlaylistMetadataGenerator,
)
from backend.features.session.infrastructure.session_summary_query import (
    SqlSessionSummaryQuery,
)
from backend.features.session.infrastructure.title_generator import (
    LLMSessionTitleGenerator,
)
from backend.features.user.application import UserMessageRateLimitService
from backend.features.user.domain import UserRepository


class SessionProvider(Provider):
    @provide(scope=Scope.APP)
    def llm_credentials(self) -> LLMCredentials:
        return LLMCredentials()

    @provide(scope=Scope.APP)
    def provide_title_generator_llm(self, credentials: LLMCredentials) -> ChatModel:
        return create_gpt_5_4(credentials=credentials)

    @provide(scope=Scope.APP)
    def provide_session_title_generator(
        self,
        llm: ChatModel,
    ) -> SessionTitleGenerator:
        return LLMSessionTitleGenerator(llm=llm)

    @provide(scope=Scope.APP)
    def provide_agent_session_event_mapper(self) -> AgentSessionEventMapper:
        return AgentSessionEventMapper()

    @provide(scope=Scope.APP)
    def provide_agent_history_builder(self) -> AgentHistoryBuilder:
        return AgentHistoryBuilder()

    @provide(scope=Scope.APP)
    def provide_session_runner(
        self,
        llm: ChatModel,
        spotify: Spotifyify,
        event_mapper: AgentSessionEventMapper,
        history_builder: AgentHistoryBuilder,
    ) -> SessionRunner:
        return AgentSessionRunner(
            llm=llm,
            spotify=spotify,
            event_mapper=event_mapper,
            history_builder=history_builder,
        )

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
    def provide_session_management_service(
        self,
        session_repository: SessionRepository,
        session_summary_query: SessionSummaryQuery,
        title_generator: SessionTitleGenerator,
    ) -> SessionService:
        return SessionService(
            session_repository=session_repository,
            session_summary_query=session_summary_query,
            title_generator=title_generator,
        )

    @provide(scope=Scope.REQUEST)
    def provide_session_conversation_service(
        self,
        session_repository: SessionRepository,
        runner: SessionRunner,
        user_message_rate_limit_service: UserMessageRateLimitService,
    ) -> SessionConversationService:
        return SessionConversationService(
            session_repository=session_repository,
            runner=runner,
            user_message_rate_limit_service=user_message_rate_limit_service,
        )

    @provide(scope=Scope.REQUEST)
    def provide_session_playlist_exporter(
        self,
        session_repository: SessionRepository,
        playlist_deck_generator: PlaylistDeckGenerator,
    ) -> SessionPlaylistExporter:
        return SessionPlaylistExporter(
            session_repository=session_repository,
            playlist_deck_generator=playlist_deck_generator,
        )

    @provide(scope=Scope.APP)
    def provide_playlist_deck_generator(self) -> PlaylistDeckGenerator:
        return TypstPlaylistDeckGenerator()

    @provide(scope=Scope.APP)
    def provide_playlist_metadata_generator(
        self,
        llm: ChatModel,
    ) -> PlaylistMetadataGenerator:
        return LLMPlaylistMetadataGenerator(llm=llm)

    @provide(scope=Scope.REQUEST)
    def provide_session_spotify_playlist_exporter(
        self,
        session_repository: SessionRepository,
        user_repository: UserRepository,
        metadata_generator: PlaylistMetadataGenerator,
        spotify_service: SpotifyService,
        spotify_token_service: SpotifyTokenService,
    ) -> SessionSpotifyPlaylistExporter:
        return SessionSpotifyPlaylistExporter(
            session_repository=session_repository,
            user_repository=user_repository,
            metadata_generator=metadata_generator,
            spotify_service=spotify_service,
            spotify_token_service=spotify_token_service,
        )
