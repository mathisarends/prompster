import asyncio
from typing import Self, cast

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine

from backend.features.health.application import ServiceNotReadyException
from backend.features.health.infrastructure.database_readiness_check import (
    DatabaseReadinessCheck,
)


class _ConnectionStub:
    def __init__(self) -> None:
        self.executed_statements: list[str] = []

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def execute(self, statement: object) -> None:
        self.executed_statements.append(str(statement))


class _EngineStub:
    def __init__(self) -> None:
        self.connection = _ConnectionStub()

    def connect(self) -> _ConnectionStub:
        return self.connection


class _FailingEngineStub:
    def connect(self) -> None:
        raise RuntimeError("database unavailable")


class TestDatabaseReadinessCheck:
    def test_check_executes_database_probe(self) -> None:
        engine = _EngineStub()
        readiness = DatabaseReadinessCheck(cast(AsyncEngine, engine))

        asyncio.run(readiness.check())

        assert engine.connection.executed_statements == ["SELECT 1"]

    def test_check_raises_when_database_is_unreachable(self) -> None:
        readiness = DatabaseReadinessCheck(cast(AsyncEngine, _FailingEngineStub()))

        with pytest.raises(ServiceNotReadyException):
            asyncio.run(readiness.check())
