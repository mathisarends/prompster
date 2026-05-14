from uuid import UUID

from backend.features.session.application.exceptions import (
    SessionNotFoundApplicationError,
)
from backend.features.session.domain import SessionNotFoundError, SessionRepository


class DeleteSessionHandler:
    def __init__(self, session_repository: SessionRepository) -> None:
        self._session_repository = session_repository

    async def handle(self, *, session_id: UUID) -> None:
        try:
            await self._session_repository.delete(session_id=session_id)
        except SessionNotFoundError as exc:
            raise SessionNotFoundApplicationError from exc
