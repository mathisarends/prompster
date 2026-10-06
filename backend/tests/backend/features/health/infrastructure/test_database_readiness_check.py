import asyncio
from typing import cast

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.features.health.application import ServiceNotReadyException
from backend.features.health.infrastructure.database_readiness_check import (
    DatabaseReadinessCheck,
)


class _SessionStub:
    def __init__(self) -> None:
        self.executed_statements: list[str] = []

    async def execute(self, statement: object) -> None:
        self.executed_statements.append(str(statement))


class _FailingSessionStub:
    async def execute(self, statement: object) -> None:
        raise RuntimeError("database unavailable")


class TestDatabaseReadinessCheck:
    def test_check_executes_database_probe(self) -> None:
        session = _SessionStub()
        readiness = DatabaseReadinessCheck(cast(AsyncSession, session))

        asyncio.run(readiness.check())

        assert session.executed_statements == ["SELECT 1"]

    def test_check_raises_when_database_is_unreachable(self) -> None:
        readiness = DatabaseReadinessCheck(cast(AsyncSession, _FailingSessionStub()))

        with pytest.raises(ServiceNotReadyException):
            asyncio.run(readiness.check())
