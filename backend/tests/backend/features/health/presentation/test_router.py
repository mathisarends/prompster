from dishka import Provider, Scope, provide
from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastapi_canon import Composition, ErrorOptions, Feature

from backend.features.health.application import (
    ReadinessCheck,
    ServiceNotReadyException,
)
from backend.features.health.presentation import HEALTH_ERRORS, health_router


class _ReadinessCheckStub(ReadinessCheck):
    def __init__(self, ready: bool) -> None:
        self._ready = ready

    async def check(self) -> None:
        if not self._ready:
            raise ServiceNotReadyException


class _StubProvider(Provider):
    def __init__(self, ready: bool) -> None:
        super().__init__()
        self._ready = ready

    @provide(scope=Scope.APP)
    def readiness_check(self) -> ReadinessCheck:
        return _ReadinessCheckStub(self._ready)


def _client(*, ready: bool = True) -> TestClient:
    app = FastAPI()
    feature = Feature(
        name="health",
        routers=[health_router],
        providers=[_StubProvider(ready)],
        errors=HEALTH_ERRORS,
    )
    Composition(
        feature, errors=ErrorOptions(type_base="https://example.test/problems")
    ).apply(app)
    return TestClient(app)


class TestHealthRouter:
    def test_health_check_returns_ok(self) -> None:
        with _client() as client:
            response = client.get("/health")

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_readiness_check_returns_ready(self) -> None:
        with _client(ready=True) as client:
            response = client.get("/readiness")

        assert response.status_code == 200
        assert response.json() == {"status": "ready"}

    def test_readiness_check_returns_service_unavailable_when_not_ready(self) -> None:
        with _client(ready=False) as client:
            response = client.get("/readiness")

        assert response.status_code == 503
        assert response.json()["code"] == "service_not_ready"
