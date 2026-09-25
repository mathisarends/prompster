from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.features.session.application.ports import ActiveSessionRunStore
from backend.platform.database.orm import ActiveSessionRunModel


class SqlActiveSessionRunStore(ActiveSessionRunStore):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def register(self, *, session_id: UUID, run_id: UUID) -> None:
        async with self._session_factory() as session:
            async with session.begin():
                active_run = await session.get(ActiveSessionRunModel, session_id)
                if active_run is None:
                    session.add(
                        ActiveSessionRunModel(
                            session_id=session_id,
                            run_id=run_id,
                            stop_requested=False,
                            updated_at=_now(),
                        )
                    )
                    return

                active_run.run_id = run_id
                active_run.stop_requested = False
                active_run.stop_requested_at = None
                active_run.updated_at = _now()

    async def complete(self, *, session_id: UUID, run_id: UUID) -> None:
        async with self._session_factory() as session:
            async with session.begin():
                await session.execute(
                    delete(ActiveSessionRunModel).where(
                        ActiveSessionRunModel.session_id == session_id,
                        ActiveSessionRunModel.run_id == run_id,
                    )
                )

    async def request_stop(self, *, session_id: UUID) -> bool:
        async with self._session_factory() as session:
            async with session.begin():
                active_run = await session.get(ActiveSessionRunModel, session_id)
                if active_run is None:
                    return False

                now = _now()
                active_run.stop_requested = True
                active_run.stop_requested_at = now
                active_run.updated_at = now
                return True

    async def is_stop_requested(self, *, session_id: UUID, run_id: UUID) -> bool:
        async with self._session_factory() as session:
            stmt = select(ActiveSessionRunModel.stop_requested).where(
                ActiveSessionRunModel.session_id == session_id,
                ActiveSessionRunModel.run_id == run_id,
            )
            return bool(await session.scalar(stmt))


def _now() -> datetime:
    return datetime.now(UTC)
