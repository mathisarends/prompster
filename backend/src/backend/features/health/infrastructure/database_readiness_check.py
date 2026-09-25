import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from backend.features.health.application import (
    ReadinessCheck,
    ServiceNotReadyException,
)

logger = logging.getLogger(__name__)


class DatabaseReadinessCheck(ReadinessCheck):
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def check(self) -> None:
        try:
            async with self._engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
        except Exception as error:
            logger.warning("Readiness check failed", exc_info=True)
            raise ServiceNotReadyException from error
