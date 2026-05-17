from uuid import UUID

from backend.features.session.application.ports.session_summary_query import (
    SessionSummary,
    SessionSummaryQuery,
)


class SearchSessionsHandler:
    def __init__(self, session_summary_query: SessionSummaryQuery) -> None:
        self._session_summary_query = session_summary_query

    async def handle(
        self,
        *,
        owner_id: UUID,
        query: str,
        limit: int,
        offset: int,
    ) -> list[SessionSummary]:
        return await self._session_summary_query.search_for_owner(
            owner_id=owner_id,
            query=query,
            limit=limit,
            offset=offset,
        )
