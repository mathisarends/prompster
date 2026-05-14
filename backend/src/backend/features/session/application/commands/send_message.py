from uuid import UUID

from backend.features.session.domain.views import SessionMessage
from backend.features.session.domain import SessionRepository


class SendMessageHandler:
    def __init__(self, session_repository: SessionRepository) -> None:
        self._session_repository = session_repository

    async def handle(self, *, session_id: UUID, content: str) -> SessionMessage:
        session = await self._session_repository.get_by_id(session_id=session_id)
        return session.add_user_message(content=content)
