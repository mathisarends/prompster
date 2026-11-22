import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.features.health.application import ReadinessCheck
from backend.features.health.domain import ServiceNotReadyException

logger = logging.getLogger(__name__)


class DatabaseReadinessCheck(ReadinessCheck):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def check(self) -> None:
        try:
            await self._session.execute(text("SELECT 1"))
        except Exception as error:
            logger.warning("Readiness check failed", exc_info=True)
            raise ServiceNotReadyException from error
