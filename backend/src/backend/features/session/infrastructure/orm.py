from uuid import UUID

from backend.features.session.domain import (
    Session,
    SessionNotFoundError,
    SessionRepository,
)


class InMemorySessionRepository(SessionRepository):
    def __init__(self) -> None:
        self._sessions: dict[UUID, Session] = {}

    async def get_by_id(self, *, session_id: UUID) -> Session:
        session = self._sessions.get(session_id)
        if session is None:
            raise SessionNotFoundError
        return session

    async def create(self, *, session: Session) -> Session:
        self._sessions[session.id] = session
        return session

    async def update(
        self,
        *,
        session_id: UUID,
        title: str | None,
        system_prompt: str | None,
    ) -> Session:
        session = self._sessions.get(session_id)
        if session is None:
            raise SessionNotFoundError

        if title is not None:
            session.title = title
        if system_prompt is not None:
            session.system_prompt = system_prompt

        self._sessions[session_id] = session
        return session

    async def delete(self, *, session_id: UUID) -> None:
        if session_id not in self._sessions:
            raise SessionNotFoundError
        del self._sessions[session_id]
