import asyncio
from uuid import uuid4

from backend.features.session.application.queries.get_session_by_id import (
    GetSessionByIdHandler,
)
from backend.features.session.domain import Session


class TestGetSessionByIdHandler:
    def test_handle_returns_given_session(self) -> None:
        session = Session(title="Roadtrip", messages=[], owner_id=uuid4())
        handler = GetSessionByIdHandler()

        result = asyncio.run(handler.handle(session=session))

        assert result is session
