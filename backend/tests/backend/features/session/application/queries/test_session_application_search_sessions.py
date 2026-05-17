import asyncio
from datetime import datetime, timezone
from uuid import UUID, uuid4

from backend.features.session.application.ports.session_summary_query import (
    SessionSummary,
    SessionSummaryQuery,
)
from backend.features.session.application.queries.search_sessions import (
    SearchSessionsHandler,
)


class _SessionSummaryQueryStub(SessionSummaryQuery):
    def __init__(self, summaries: list[SessionSummary]) -> None:
        self._summaries = summaries
        self.received_owner_id: UUID | None = None
        self.received_query: str | None = None
        self.received_limit: int | None = None
        self.received_offset: int | None = None

    async def list_for_owner(
        self,
        *,
        owner_id: UUID,
        limit: int,
        offset: int,
    ) -> list[SessionSummary]:
        raise AssertionError(
            "list_for_owner is not used in SearchSessionsHandler tests"
        )

    async def search_for_owner(
        self,
        *,
        owner_id: UUID,
        query: str,
        limit: int,
        offset: int,
    ) -> list[SessionSummary]:
        self.received_owner_id = owner_id
        self.received_query = query
        self.received_limit = limit
        self.received_offset = offset
        return self._summaries


class TestSearchSessionsHandler:
    def test_handle_delegates_to_session_summary_query(self) -> None:
        owner_id = uuid4()
        summaries = [
            SessionSummary(
                id=uuid4(),
                title="Techno Mix",
                created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
                last_activity_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
            )
        ]
        query = _SessionSummaryQueryStub(summaries=summaries)
        handler = SearchSessionsHandler(session_summary_query=query)

        result = asyncio.run(
            handler.handle(owner_id=owner_id, query="techno", limit=5, offset=15)
        )

        assert result == summaries
        assert query.received_owner_id == owner_id
        assert query.received_query == "techno"
        assert query.received_limit == 5
        assert query.received_offset == 15
