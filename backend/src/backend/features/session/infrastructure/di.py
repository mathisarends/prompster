from dishka import Provider, Scope, provide

from backend.features.session.application import (
    CreateSessionHandler,
    DeleteSessionHandler,
    GetSessionByIdHandler,
    SendMessageHandler,
    UpdateSessionHandler,
)
from backend.features.session.application.ports.title_generator import (
    SessionTitleGenerator,
)
from backend.features.session.domain import SessionRepository
from backend.features.session.infrastructure.impl.title_generator import (
    LLMSessionTitleGenerator,
)
from backend.features.session.infrastructure.orm import InMemorySessionRepository
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

    @provide(scope=Scope.APP)
    def provide_session_repository(self) -> SessionRepository:
        return InMemorySessionRepository()

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
    def provide_update_session_handler(
        self,
        session_repository: SessionRepository,
    ) -> UpdateSessionHandler:
        return UpdateSessionHandler(session_repository=session_repository)

    @provide(scope=Scope.REQUEST)
    def provide_send_message_handler(
        self,
        session_repository: SessionRepository,
        llm: ChatOpenAI,
    ) -> SendMessageHandler:
        return SendMessageHandler(session_repository=session_repository, llm=llm)

    @provide(scope=Scope.REQUEST)
    def provide_delete_session_handler(
        self,
        session_repository: SessionRepository,
    ) -> DeleteSessionHandler:
        return DeleteSessionHandler(session_repository=session_repository)
