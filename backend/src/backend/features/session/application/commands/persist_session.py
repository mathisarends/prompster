from backend.features.session.domain import Session, SessionRepository


class PersistSessionHandler:
    def __init__(self, session_repository: SessionRepository) -> None:
        self._session_repository = session_repository

    async def handle(self, *, session: Session) -> Session:
        return await self._session_repository.save(session=session)
