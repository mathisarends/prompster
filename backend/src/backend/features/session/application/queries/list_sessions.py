from uuid import UUID

from backend.features.session.application.ports.session_summary_query import (
    SessionSummary,
    SessionSummaryQuery,
)


class ListSessionsHandler:
    def __init__(self, session_summary_query: SessionSummaryQuery) -> None:
        self._session_summary_query = session_summary_query

    async def handle(
        self,
        *,
        owner_id: UUID,
        limit: int,
        offset: int,
    ) -> list[SessionSummary]:
        return await self._session_summary_query.list_for_owner(
            owner_id=owner_id,
            limit=limit,
            offset=offset,
        )
