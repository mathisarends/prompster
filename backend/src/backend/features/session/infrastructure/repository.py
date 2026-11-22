from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.features.session.domain import (
    Session,
    SessionNotFoundError,
    SessionRepository,
)
from backend.features.session.infrastructure.orm_mapper import SessionOrmMapper
from backend.platform.database import Repository
from backend.platform.database.orm import (
    SessionModel,
    SessionPlaylistModel,
    SessionToolCallSequenceModel,
    SessionUserMessageModel,
)


class SqlSessionRepository(Repository[SessionModel, Session], SessionRepository):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session=session, model=SessionModel)
        self._mapper = SessionOrmMapper()

    async def get_by_id(self, *, session_id: UUID) -> Session:
        session = await self.session.scalar(self._detail_query(session_id=session_id))
        if session is None:
            raise SessionNotFoundError
        return self._to_domain(session)

    async def update(
        self,
        *,
        session_id: UUID,
        title: str | None,
    ) -> Session:
        session = await self.get_by_id(session_id=session_id)
        if title is not None:
            session.title = title
        return await self.save(session=session)

    async def delete(self, *, session_id: UUID) -> None:
        deleted = await self.delete_by_id(session_id)
        if not deleted:
            raise SessionNotFoundError

    async def save(self, *, session: Session) -> Session:
        orm = await self.session.scalar(self._detail_query(session_id=session.id))
        if orm is None:
            orm = SessionModel(id=session.id)
            self.session.add(orm)

        self._mapper.sync(orm=orm, session=session)

        await self.session.flush()
        return self._to_domain(orm)

    def _to_domain(self, orm: SessionModel) -> Session:
        return self._mapper.to_domain(orm)

    def _to_orm(self, domain: Session) -> SessionModel:
        return self._mapper.to_orm(domain)

    def _detail_query(self, *, session_id: UUID):
        return (
            select(SessionModel)
            .where(SessionModel.id == session_id)
            .options(
                selectinload(SessionModel.user_messages).selectinload(
                    SessionUserMessageModel.attachments
                ),
                selectinload(SessionModel.user_messages).selectinload(
                    SessionUserMessageModel.image_attachments
                ),
                selectinload(SessionModel.assistant_messages),
                selectinload(SessionModel.user_curation_events),
                selectinload(SessionModel.playlist_references),
                selectinload(SessionModel.artist_references),
                selectinload(SessionModel.onboarding_questions),
                selectinload(SessionModel.tool_call_sequences).selectinload(
                    SessionToolCallSequenceModel.calls
                ),
                selectinload(SessionModel.playlist).selectinload(
                    SessionPlaylistModel.tracks
                ),
            )
        )
