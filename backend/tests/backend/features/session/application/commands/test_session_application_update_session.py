import asyncio
from uuid import UUID, uuid4

from backend.features.session.application.commands.update_session import (
    UpdateSessionHandler,
)
from backend.features.session.domain import Session, SessionRepository


class _SessionRepositoryStub(SessionRepository):
    def __init__(self, updated_session: Session) -> None:
        self._updated_session = updated_session
        self.received_session_id: UUID | None = None
        self.received_title: str | None = None

    async def get_by_id(self, session_id: UUID) -> Session:
        raise AssertionError("get_by_id is not used in UpdateSessionHandler tests")

    async def create(self, session: Session) -> Session:
        raise AssertionError("create is not used in UpdateSessionHandler tests")

    async def update(self, session_id: UUID, title: str | None) -> Session:
        self.received_session_id = session_id
        self.received_title = title
        return self._updated_session

    async def delete(self, session_id: UUID) -> None:
        raise AssertionError("delete is not used in UpdateSessionHandler tests")


class TestUpdateSessionHandler:
    def test_handle_delegates_to_repository_and_returns_updated_session(self) -> None:
        session = Session(title="Old", messages=[], owner_id=uuid4())
        updated = Session(
            title="New", messages=[], owner_id=session.owner_id, id=session.id
        )
        repository = _SessionRepositoryStub(updated_session=updated)
        handler = UpdateSessionHandler(session_repository=repository)

        result = asyncio.run(handler.handle(session=session, title="New"))

        assert result is updated
        assert repository.received_session_id == session.id
        assert repository.received_title == "New"
