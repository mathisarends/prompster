from dataclasses import replace
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.features.session.application.ports import (
    SessionSummary,
    SessionSummaryQuery,
)
from backend.platform.database import (
    PlaylistTrackModel,
    SessionModel,
    SessionPlaylistModel,
)

# A deck shows a 2x2 mosaic like a Spotify playlist, so four covers are enough.
_MOSAIC_SIZE = 4


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
        stmt = self._select(owner_id)
        return await self._fetch(stmt, limit=limit, offset=offset)

    async def search_for_owner(
        self,
        *,
        owner_id: UUID,
        query: str,
        limit: int,
        offset: int,
    ) -> list[SessionSummary]:
        stmt = self._select(owner_id).where(
            SessionModel.title.ilike(f"%{query.strip()}%")
        )
        return await self._fetch(stmt, limit=limit, offset=offset)

    @staticmethod
    def _select(owner_id: UUID) -> Select:
        return select(
            SessionModel.id,
            SessionModel.title,
            SessionModel.is_starred,
            SessionModel.created_at,
            SessionModel.last_activity_at,
        ).where(SessionModel.owner_id == owner_id)

    async def _fetch(
        self, stmt: Select, *, limit: int, offset: int
    ) -> list[SessionSummary]:
        page = (
            stmt.order_by(SessionModel.last_activity_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(page)
        summaries = [
            SessionSummary(
                id=row.id,
                title=row.title,
                is_starred=row.is_starred,
                created_at=row.created_at or row.last_activity_at,
                last_activity_at=row.last_activity_at or row.created_at,
            )
            for row in result.all()
        ]
        session_ids = [summary.id for summary in summaries]
        covers = await self._covers(session_ids)
        return [
            replace(summary, cover_urls=tuple(covers.get(summary.id, [])))
            for summary in summaries
        ]

    async def _covers(self, session_ids: list[UUID]) -> dict[UUID, list[str]]:
        """First distinct track covers per deck, in playlist order."""
        if not session_ids:
            return {}
        stmt = (
            select(SessionPlaylistModel.session_id, PlaylistTrackModel.cover_url)
            .join(
                SessionPlaylistModel,
                PlaylistTrackModel.playlist_id == SessionPlaylistModel.id,
            )
            .where(SessionPlaylistModel.session_id.in_(session_ids))
            .where(PlaylistTrackModel.cover_url.is_not(None))
            .order_by(SessionPlaylistModel.session_id, PlaylistTrackModel.position)
        )
        result = await self._session.execute(stmt)
        covers: dict[UUID, list[str]] = {}
        for session_id, cover_url in result.all():
            deck = covers.setdefault(session_id, [])
            if len(deck) < _MOSAIC_SIZE and cover_url not in deck:
                deck.append(cover_url)
        return covers
