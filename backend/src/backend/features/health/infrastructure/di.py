from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import AsyncEngine

from backend.features.health.application import ReadinessCheck
from backend.features.health.infrastructure.database_readiness_check import (
    DatabaseReadinessCheck,
)


class HealthProvider(Provider):
    @provide(scope=Scope.APP)
    def readiness_check(self, engine: AsyncEngine) -> ReadinessCheck:
        return DatabaseReadinessCheck(engine)
