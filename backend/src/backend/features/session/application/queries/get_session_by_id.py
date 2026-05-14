from uuid import UUID

from backend.features.session.domain import Session, SessionRepository


class GetSessionByIdHandler:
    def __init__(self, session_repository: SessionRepository) -> None:
        self._session_repository = session_repository

    async def handle(self, *, session_id: UUID) -> Session:
        return await self._session_repository.get_by_id(session_id=session_id)
