import asyncio
from uuid import UUID, uuid4

import pytest

from backend.features.session.application.queries.get_session_by_id import (
    GetSessionByIdHandler,
)
from backend.features.session.domain import (
    Session,
    SessionAccessDeniedError,
    SessionRepository,
)


class _SessionRepositoryStub(SessionRepository):
    def __init__(self, session: Session) -> None:
        self._session = session
        self.received_session_id: UUID | None = None

    async def get_by_id(self, session_id: UUID) -> Session:
        self.received_session_id = session_id
        return self._session

    async def create(self, session: Session) -> Session:
        raise AssertionError("create is not used in GetSessionByIdHandler tests")

    async def save(self, *, session: Session) -> Session:
        raise AssertionError("save is not used in GetSessionByIdHandler tests")

    async def update(self, session_id: UUID, title: str | None) -> Session:
        raise AssertionError("update is not used in GetSessionByIdHandler tests")

    async def delete(self, session_id: UUID) -> None:
        raise AssertionError("delete is not used in GetSessionByIdHandler tests")


class TestGetSessionByIdHandler:
    def test_handle_loads_session_and_allows_owner(self) -> None:
        owner_id = uuid4()
        session = Session(title="Roadtrip", messages=[], owner_id=owner_id)
        repository = _SessionRepositoryStub(session=session)
        handler = GetSessionByIdHandler(session_repository=repository)

        result = asyncio.run(handler.handle(session_id=session.id, user_id=owner_id))

        assert result is session
        assert repository.received_session_id == session.id

    def test_handle_raises_when_user_does_not_own_session(self) -> None:
        session = Session(title="Roadtrip", messages=[], owner_id=uuid4())
        repository = _SessionRepositoryStub(session=session)
        handler = GetSessionByIdHandler(session_repository=repository)

        with pytest.raises(SessionAccessDeniedError, match="does not have access"):
            asyncio.run(handler.handle(session_id=session.id, user_id=uuid4()))
