from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.features.session.application.ports.session_summary_query import (
    SessionSummary,
    SessionSummaryQuery,
)
from backend.infrastructure.database.orm import SessionModel


class SqlSessionSummaryQuery(SessionSummaryQuery):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_for_owner(
        self,
        *,
        owner_id: UUID,
        limit: int,
        offset: int,
    ) -> list[SessionSummary]:
        stmt = (
            select(
                SessionModel.id,
                SessionModel.title,
                SessionModel.created_at,
                SessionModel.last_activity_at,
            )
            .where(SessionModel.owner_id == owner_id)
            .order_by(SessionModel.last_activity_at.desc())
            .limit(limit)
            .offset(offset)
        )
        rows = (await self._session.execute(stmt)).all()
        return [
            SessionSummary(
                id=row.id,
                title=row.title,
                created_at=row.created_at or row.last_activity_at,
                last_activity_at=row.last_activity_at or row.created_at,
            )
            for row in rows
        ]

    async def search_for_owner(
        self,
        *,
        owner_id: UUID,
        query: str,
        limit: int,
        offset: int,
    ) -> list[SessionSummary]:
        stmt = (
            select(
                SessionModel.id,
                SessionModel.title,
                SessionModel.created_at,
                SessionModel.last_activity_at,
            )
            .where(SessionModel.owner_id == owner_id)
            .where(SessionModel.title.ilike(f"%{query.strip()}%"))
            .order_by(SessionModel.last_activity_at.desc())
            .limit(limit)
            .offset(offset)
        )
        rows = (await self._session.execute(stmt)).all()
        return [
            SessionSummary(
                id=row.id,
                title=row.title,
                created_at=row.created_at or row.last_activity_at,
                last_activity_at=row.last_activity_at or row.created_at,
            )
            for row in rows
        ]
