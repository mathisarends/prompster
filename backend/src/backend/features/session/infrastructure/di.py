from dishka import Provider, Scope, provide
from pydantic_ai.models import Model
from spotifyify import SpotifyClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.features.llm.application import ChatModels
from backend.features.llm.domain import LLMRegistry
from backend.features.oauth_connections.application import SpotifyTokenService
from backend.features.session.application import (
    ImageAttachmentService,
    SessionConversationService,
    SessionImageUrlResolver,
    SessionPlaylistExporter,
    SessionService,
    SessionSpotifyPlaylistExporter,
)
from backend.features.session.application.ports import (
    ActiveSessionRunStore,
    MessageAttachmentStore,
    PlaylistDeckGenerator,
    PlaylistMetadataGenerator,
    SessionRunner,
    SessionSummaryQuery,
    SessionTitleGenerator,
)
from backend.features.session.domain import SessionRepository
from backend.features.session.infrastructure.active_run_store import (
    SqlActiveSessionRunStore,
)
from backend.features.session.infrastructure.agent_checkpoint_store import (
    SqlAgentCheckpointStore,
)
from backend.features.session.infrastructure.agent_input import AgentInputBuilder
from backend.features.session.infrastructure.message_attachment_store import (
    StorageMessageAttachmentStore,
)
from backend.features.session.infrastructure.pdf_generator import (
    TypstPlaylistDeckGenerator,
)
from backend.features.session.infrastructure.playlist_metadata_generator import (
    LLMPlaylistMetadataGenerator,
)
from backend.features.session.infrastructure.repository import SqlSessionRepository
from backend.features.session.infrastructure.session_runner import (
    AgentRuntimeRegistry,
    AgentSessionRunner,
)
from backend.features.session.infrastructure.session_summary_query import (
    SqlSessionSummaryQuery,
)
from backend.features.session.infrastructure.title_generator import (
    LLMSessionTitleGenerator,
)
from backend.features.spotify.application import SpotifyPlaylistCreator
from backend.features.user.domain import UserRepository
from backend.shared.storage import ObjectStorage


class SessionProvider(Provider):
    @provide(scope=Scope.APP)
    def provide_session_title_generator(
        self,
        llm: Model,
    ) -> SessionTitleGenerator:
        return LLMSessionTitleGenerator(llm=llm)

    @provide(scope=Scope.APP)
    def provide_message_attachment_store(
        self,
        storage_backend: ObjectStorage,
    ) -> MessageAttachmentStore:
        return StorageMessageAttachmentStore(storage_backend=storage_backend)

    @provide(scope=Scope.APP)
    def provide_agent_input_builder(
        self,
        message_attachment_store: MessageAttachmentStore,
    ) -> AgentInputBuilder:
        return AgentInputBuilder(message_attachment_store=message_attachment_store)

    @provide(scope=Scope.APP)
    def provide_agent_checkpoint_store(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> SqlAgentCheckpointStore:
        return SqlAgentCheckpointStore(session_factory=session_factory)

    @provide(scope=Scope.APP)
    def provide_active_session_run_store(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> ActiveSessionRunStore:
        return SqlActiveSessionRunStore(session_factory=session_factory)

    @provide(scope=Scope.APP)
    def provide_agent_runtime_registry(self) -> AgentRuntimeRegistry:
        return AgentRuntimeRegistry()

    @provide(scope=Scope.APP)
    def provide_session_runner(
        self,
        llm: Model,
        chat_models: ChatModels,
        spotify: SpotifyClient,
        input_builder: AgentInputBuilder,
        checkpoints: SqlAgentCheckpointStore,
        *,
        active_runs: ActiveSessionRunStore,
        runtime_registry: AgentRuntimeRegistry,
        llm_registry: LLMRegistry,
    ) -> SessionRunner:
        return AgentSessionRunner(
            llm=llm,
            chat_models=chat_models,
            spotify=spotify,
            input_builder=input_builder,
            checkpoints=checkpoints,
            active_runs=active_runs,
            runtime_registry=runtime_registry,
            llm_registry=llm_registry,
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
    def provide_session_image_url_resolver(
        self,
        message_attachment_store: MessageAttachmentStore,
    ) -> SessionImageUrlResolver:
        return SessionImageUrlResolver(
            message_attachment_store=message_attachment_store,
        )

    @provide(scope=Scope.REQUEST)
    def provide_session_conversation_service(
        self,
        session_repository: SessionRepository,
        runner: SessionRunner,
        message_attachment_store: MessageAttachmentStore,
        title_generator: SessionTitleGenerator,
    ) -> SessionConversationService:
        return SessionConversationService(
            session_repository=session_repository,
            runner=runner,
            message_attachment_store=message_attachment_store,
            title_generator=title_generator,
        )

    @provide(scope=Scope.REQUEST)
    def provide_session_playlist_exporter(
        self,
        session_repository: SessionRepository,
        playlist_deck_generator: PlaylistDeckGenerator,
        storage_backend: ObjectStorage,
    ) -> SessionPlaylistExporter:
        return SessionPlaylistExporter(
            session_repository=session_repository,
            playlist_deck_generator=playlist_deck_generator,
            storage_backend=storage_backend,
        )

    @provide(scope=Scope.APP)
    def provide_playlist_deck_generator(self) -> PlaylistDeckGenerator:
        return TypstPlaylistDeckGenerator()

    @provide(scope=Scope.APP)
    def provide_playlist_metadata_generator(
        self,
        llm: Model,
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
