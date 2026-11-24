from uuid import UUID

from agent import AgentCheckpoint, AgentCommit
from sqlalchemy import update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.platform.database import SessionAgentCheckpointModel


class SqlAgentCheckpointStore:
    """Keeps each session's agent checkpoint in two JSONB columns.

    A commit rewrites ``execution`` every time and ``state`` only when the
    settled history changed, so most writes stay small.
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def load(self, *, session_id: UUID) -> AgentCheckpoint | None:
        async with self._session_factory() as session:
            row = await session.get(SessionAgentCheckpointModel, session_id)
            if row is None:
                return None
            return AgentCheckpoint(state=row.state, execution=row.execution)

    async def save(self, *, session_id: UUID, commit: AgentCommit) -> None:
        async with self._session_factory() as session, session.begin():
            if commit.state is None:
                await session.execute(
                    update(SessionAgentCheckpointModel)
                    .where(SessionAgentCheckpointModel.session_id == session_id)
                    .values(execution=dict(commit.execution))
                )
                return
            values = {
                "state": dict(commit.state),
                "execution": dict(commit.execution),
            }
            await session.execute(
                insert(SessionAgentCheckpointModel)
                .values(session_id=session_id, **values)
                .on_conflict_do_update(
                    index_elements=[SessionAgentCheckpointModel.session_id],
                    set_=values,
                )
            )
