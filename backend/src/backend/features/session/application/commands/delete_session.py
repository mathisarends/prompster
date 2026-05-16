from backend.features.session.domain import Session, SessionRepository


class DeleteSessionHandler:
    def __init__(self, session_repository: SessionRepository) -> None:
        self._session_repository = session_repository

    async def handle(self, *, session: Session) -> None:
        await self._session_repository.delete(session_id=session.id)
