import asyncio
from uuid import UUID, uuid4

from backend.features.session.application.commands.delete_session import (
    DeleteSessionHandler,
)
from backend.features.session.domain import Session, SessionRepository


class _SessionRepositoryStub(SessionRepository):
    def __init__(self) -> None:
        self.deleted_session_id: UUID | None = None

    async def get_by_id(self, session_id: UUID) -> Session:
        raise AssertionError("get_by_id is not used in DeleteSessionHandler tests")

    async def create(self, session: Session) -> Session:
        raise AssertionError("create is not used in DeleteSessionHandler tests")

    async def save(self, *, session: Session) -> Session:
        raise AssertionError("save is not used in DeleteSessionHandler tests")

    async def update(self, session_id: UUID, title: str | None) -> Session:
        raise AssertionError("update is not used in DeleteSessionHandler tests")

    async def delete(self, session_id: UUID) -> None:
        self.deleted_session_id = session_id


class TestDeleteSessionHandler:
    def test_handle_deletes_session_by_id(self) -> None:
        repository = _SessionRepositoryStub()
        handler = DeleteSessionHandler(session_repository=repository)
        session = Session(title="Roadtrip", messages=[], owner_id=uuid4())

        asyncio.run(handler.handle(session=session))

        assert repository.deleted_session_id == session.id
