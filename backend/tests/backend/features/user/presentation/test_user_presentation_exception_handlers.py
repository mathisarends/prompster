import asyncio
from datetime import datetime, timedelta, timezone

from starlette.requests import Request

from backend.features.user.domain import UserMessageQuotaExceededError
from backend.features.user.presentation.exception_handlers import (
    _user_message_quota_exceeded_handler,
)


class TestUserQuotaExceptionHandler:
    def test_returns_429_with_retry_after_and_quota_payload(self) -> None:
        now = datetime.now(timezone.utc)
        exc = UserMessageQuotaExceededError(
            limit=50, reset_at=now + timedelta(minutes=5)
        )
        request = Request(scope={"type": "http"})

        response = asyncio.run(_user_message_quota_exceeded_handler(request, exc))

        assert response.status_code == 429
        assert int(response.headers["Retry-After"]) >= 1
        assert b'"limit":50' in response.body
        assert b'"remaining":0' in response.body
