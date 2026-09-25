from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import AsyncSession

from backend.features.health.application import ReadinessCheck
from backend.features.health.infrastructure.database_readiness_check import (
    DatabaseReadinessCheck,
)


class HealthProvider(Provider):
    @provide(scope=Scope.REQUEST)
    def readiness_check(self, session: AsyncSession) -> ReadinessCheck:
        return DatabaseReadinessCheck(session)
