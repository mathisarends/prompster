from dishka import Provider, Scope, provide
from llm import LLMCredentials, create_gpt_5_4_mini
from llmify import ChatModel
from sqlalchemy.ext.asyncio import AsyncSession
from spotifyify import Spotifyify

from backend.features.oauth_connections.application import SpotifyTokenService
from backend.features.spotify.application.ports import SpotifyPlaylistCreator
from backend.features.session.application import (
    ImageAttachmentService,
    SessionPlaylistExporter,
    SessionConversationService,
    SessionService,
    SessionSpotifyPlaylistExporter,
)
from backend.features.session.application.ports import (
    MessageAttachmentStore,
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
from backend.features.session.infrastructure.pdf_generator import (
    TypstPlaylistDeckGenerator,
)
from backend.features.session.infrastructure.playlist_metadata_generator import (
    LLMPlaylistMetadataGenerator,
)
from backend.features.session.infrastructure.message_attachment_store import (
    StorageMessageAttachmentStore,
)
from backend.features.session.infrastructure.repository import SqlSessionRepository
from backend.features.session.infrastructure.session_runner import AgentSessionRunner
from backend.features.session.infrastructure.session_summary_query import (
    SqlSessionSummaryQuery,
)
from backend.features.session.infrastructure.title_generator import (
    LLMSessionTitleGenerator,
)
from backend.features.user.application import UserMessageRateLimitService
from backend.features.user.domain import UserRepository
from backend.infrastructure.storage import StorageBackend


class SessionProvider(Provider):
    @provide(scope=Scope.APP)
    def llm_credentials(self) -> LLMCredentials:
        return LLMCredentials()

    @provide(scope=Scope.APP)
    def provide_llm(self, credentials: LLMCredentials) -> ChatModel:
        return create_gpt_5_4_mini(credentials=credentials)

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
    def provide_message_attachment_store(
        self,
        storage_backend: StorageBackend,
    ) -> MessageAttachmentStore:
        return StorageMessageAttachmentStore(storage_backend=storage_backend)

    @provide(scope=Scope.APP)
    def provide_agent_history_builder(
        self,
        message_attachment_store: MessageAttachmentStore,
    ) -> AgentHistoryBuilder:
        return AgentHistoryBuilder(message_attachment_store=message_attachment_store)

    @provide(scope=Scope.APP)
    def provide_session_runner(
        self,
        llm: ChatModel,
        credentials: LLMCredentials,
        spotify: Spotifyify,
        event_mapper: AgentSessionEventMapper,
        history_builder: AgentHistoryBuilder,
    ) -> SessionRunner:
        return AgentSessionRunner(
            llm=llm,
            llm_credentials=credentials,
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
        message_attachment_store: MessageAttachmentStore,
    ) -> SessionService:
        return SessionService(
            session_repository=session_repository,
            session_summary_query=session_summary_query,
            message_attachment_store=message_attachment_store,
        )

    @provide(scope=Scope.REQUEST)
    def provide_image_attachment_service(
        self,
        message_attachment_store: MessageAttachmentStore,
    ) -> ImageAttachmentService:
        return ImageAttachmentService(
            message_attachment_store=message_attachment_store,
        )

    @provide(scope=Scope.REQUEST)
    def provide_session_conversation_service(
        self,
        session_repository: SessionRepository,
        runner: SessionRunner,
        message_attachment_store: MessageAttachmentStore,
        user_message_rate_limit_service: UserMessageRateLimitService,
        title_generator: SessionTitleGenerator,
    ) -> SessionConversationService:
        return SessionConversationService(
            session_repository=session_repository,
            runner=runner,
            message_attachment_store=message_attachment_store,
            user_message_rate_limit_service=user_message_rate_limit_service,
            title_generator=title_generator,
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
        spotify_playlist_creator: SpotifyPlaylistCreator,
        spotify_token_service: SpotifyTokenService,
    ) -> SessionSpotifyPlaylistExporter:
        return SessionSpotifyPlaylistExporter(
            session_repository=session_repository,
            user_repository=user_repository,
            metadata_generator=metadata_generator,
            spotify_playlist_creator=spotify_playlist_creator,
            spotify_token_service=spotify_token_service,
        )
