from dishka import Provider, Scope, provide

from backend.features.session.application import (
    CreateSessionHandler,
    DeleteSessionHandler,
    GetSessionByIdHandler,
    UpdateSessionHandler,
)
from backend.features.session.domain import SessionRepository
from backend.features.session.infrastructure.orm import InMemorySessionRepository


class SessionProvider(Provider):
    @provide(scope=Scope.APP)
    def provide_session_repository(self) -> SessionRepository:
        return InMemorySessionRepository()

    @provide(scope=Scope.REQUEST)
    def provide_create_session_handler(
        self,
        session_repository: SessionRepository,
    ) -> CreateSessionHandler:
        return CreateSessionHandler(session_repository=session_repository)

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
    def provide_delete_session_handler(
        self,
        session_repository: SessionRepository,
    ) -> DeleteSessionHandler:
        return DeleteSessionHandler(session_repository=session_repository)
