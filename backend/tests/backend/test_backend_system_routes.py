import asyncio
import json
from typing import Any, cast

from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from sqlalchemy.ext.asyncio import AsyncEngine

from backend.presentation.health_router import (
    health_check,
    health_router,
    readiness_check,
)


class _ConnectionStub:
    def __init__(self) -> None:
        self.executed_statements: list[str] = []

    async def __aenter__(self) -> "_ConnectionStub":
        return self

    async def __aexit__(self, *args: Any) -> None:
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


class TestSystemRoutes:
    def test_registers_health_and_readiness_routes(self) -> None:
        route_paths = {
            route.path for route in health_router.routes if isinstance(route, APIRoute)
        }

        assert route_paths == {"/health", "/readiness"}

    def test_health_check_returns_ok(self) -> None:
        response = asyncio.run(health_check())

        assert response == {"status": "ok"}

    def test_readiness_check_executes_database_probe(self) -> None:
        engine = _EngineStub()

        response = asyncio.run(readiness_check(cast(AsyncEngine, engine)))

        assert response == {"status": "ready"}
        assert engine.connection.executed_statements == ["SELECT 1"]

    def test_readiness_check_returns_service_unavailable_on_probe_failure(self) -> None:
        response = asyncio.run(readiness_check(cast(AsyncEngine, _FailingEngineStub())))

        assert isinstance(response, JSONResponse)
        assert response.status_code == 503
        assert json.loads(response.body) == {"status": "not_ready"}
