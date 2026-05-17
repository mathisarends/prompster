from collections.abc import AsyncGenerator

from dishka import Provider, Scope, provide
from llmify import ChatOpenAI
from sqlalchemy.ext.asyncio import AsyncSession
from spotifyify import SpotifyCredentials, Spotifyify
from spotifyify.cache_handler import MemoryCacheHandler

from backend.env import LLMCredentials
from backend.features.session.infrastructure.repository import SqlSessionRepository

from backend.features.session.application import (
    AddPlaylistTrackHandler,
    AnswerFollowUpWithOptionHandler,
    AnswerFollowUpWithTextHandler,
    AppendUserMessageHandler,
    CreateSessionHandler,
    DeleteSessionHandler,
    GetSessionByIdHandler,
    ListSessionsHandler,
    PersistSessionHandler,
    RemovePlaylistTrackHandler,
    SearchSpotifyTracksHandler,
    SearchSessionsHandler,
    SendMessageHandler,
    SkipFollowUpHandler,
    UpdateSessionHandler,
)
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
        session_repository: SessionRepository,
    ) -> GetSessionByIdHandler:
        return GetSessionByIdHandler(session_repository=session_repository)

    @provide(scope=Scope.REQUEST)
    def provide_append_user_message_handler(self) -> AppendUserMessageHandler:
        return AppendUserMessageHandler()

    @provide(scope=Scope.REQUEST)
    def provide_answer_follow_up_with_option_handler(
        self,
    ) -> AnswerFollowUpWithOptionHandler:
        return AnswerFollowUpWithOptionHandler()

    @provide(scope=Scope.REQUEST)
    def provide_answer_follow_up_with_text_handler(
        self,
    ) -> AnswerFollowUpWithTextHandler:
        return AnswerFollowUpWithTextHandler()

    @provide(scope=Scope.REQUEST)
    def provide_skip_follow_up_handler(self) -> SkipFollowUpHandler:
        return SkipFollowUpHandler()

    @provide(scope=Scope.REQUEST)
    def provide_add_playlist_track_handler(self) -> AddPlaylistTrackHandler:
        return AddPlaylistTrackHandler()

    @provide(scope=Scope.REQUEST)
    def provide_remove_playlist_track_handler(self) -> RemovePlaylistTrackHandler:
        return RemovePlaylistTrackHandler()

    @provide(scope=Scope.REQUEST)
    def provide_persist_session_handler(
        self,
        session_repository: SessionRepository,
    ) -> PersistSessionHandler:
        return PersistSessionHandler(session_repository=session_repository)

    @provide(scope=Scope.REQUEST)
    def provide_list_sessions_handler(
        self,
        session_summary_query: SessionSummaryQuery,
    ) -> ListSessionsHandler:
        return ListSessionsHandler(session_summary_query=session_summary_query)

    @provide(scope=Scope.REQUEST)
    def provide_search_sessions_handler(
        self,
        session_summary_query: SessionSummaryQuery,
    ) -> SearchSessionsHandler:
        return SearchSessionsHandler(session_summary_query=session_summary_query)

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
