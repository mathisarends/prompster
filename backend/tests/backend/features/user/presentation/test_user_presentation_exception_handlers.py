from datetime import UTC, datetime, timedelta

from backend.features.user.domain import UserMessageQuotaExceededError
from backend.features.user.presentation.exception_handlers import (
    USER_ERRORS,
    USER_MESSAGE_QUOTA_EXCEEDED_ERROR,
)
from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastapi_canon import ErrorRegistry


class TestUserQuotaExceptionHandler:
    def test_returns_problem_with_retry_after_and_quota_extensions(self) -> None:
        reset_at = datetime.now(UTC) + timedelta(minutes=5)
        app = FastAPI()

        @app.get(
            "/quota",
            responses=USER_ERRORS.responses(USER_MESSAGE_QUOTA_EXCEEDED_ERROR),
        )
        async def quota() -> None:
            raise UserMessageQuotaExceededError(limit=50, reset_at=reset_at)

        registry = ErrorRegistry.merge(
            USER_ERRORS,
            name="test",
            type_base="https://api.prompster.dev/problems",
        )
        registry.install(
            app,
            include_validation_error=False,
            include_http_exceptions=False,
            include_unhandled_error=False,
        )

        response = TestClient(app).get("/quota")

        assert response.status_code == 429
        assert response.headers["content-type"] == "application/problem+json"
        assert int(response.headers["Retry-After"]) >= 1
        assert response.json() == {
            "type": ("https://api.prompster.dev/problems/user_message_quota_exceeded"),
            "title": "User message quota exceeded",
            "status": 429,
            "code": "user_message_quota_exceeded",
            "limit": 50,
            "remaining": 0,
            "reset_at": reset_at.isoformat().replace("+00:00", "Z"),
        }
