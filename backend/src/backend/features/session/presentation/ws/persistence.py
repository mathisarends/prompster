import asyncio
import logging
from uuid import UUID

from dishka import AsyncContainer

from backend.features.session.application import PersistSessionHandler
from backend.features.session.domain import Session

logger = logging.getLogger(__name__)


class SessionPersistenceDaemon:
    def __init__(self, *, container: AsyncContainer, session_id: UUID) -> None:
        self._container = container
        self._session_id = session_id
        self._queue: asyncio.Queue[Session | None] = asyncio.Queue()
        self._task: asyncio.Task[None] | None = None

    def start(self) -> None:
        if self._task is not None:
            return
        self._task = asyncio.create_task(
            self._run(),
            name=f"session-{self._session_id}-persistence",
        )

    def persist(self, session: Session) -> None:
        if self._task is None:
            raise RuntimeError("Session persistence daemon has not been started.")
        self._queue.put_nowait(session)

    async def close(self) -> None:
        task = self._task
        if task is None:
            return

        await self._queue.join()
        self._queue.put_nowait(None)
        await task
        self._task = None

    async def _run(self) -> None:
        while True:
            session = await self._queue.get()
            try:
                if session is None:
                    return
                await self._persist(session)
            except Exception:
                logger.exception("Failed to persist session %s", self._session_id)
            finally:
                self._queue.task_done()

    async def _persist(self, session: Session) -> None:
        async with self._container() as request_container:
            handler = await request_container.get(PersistSessionHandler)
            await handler.handle(session=session)
