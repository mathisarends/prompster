from datetime import datetime, timezone

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from backend.features.user.domain import UserMessageQuotaExceededError


def _exception_detail(exc: Exception, *, fallback: str) -> str:
    detail = str(exc).strip()
    return detail if detail else fallback


async def _user_message_quota_exceeded_handler(
    _: Request,
    exc: UserMessageQuotaExceededError,
) -> JSONResponse:
    retry_after = max(
        1,
        int((exc.reset_at - datetime.now(timezone.utc)).total_seconds()),
    )
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        headers={"Retry-After": str(retry_after)},
        content={
            "detail": _exception_detail(
                exc,
                fallback="Daily agent message limit reached",
            ),
            "limit": exc.limit,
            "remaining": 0,
            "reset_at": exc.reset_at.isoformat(),
        },
    )


def register_user_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(
        UserMessageQuotaExceededError,
        _user_message_quota_exceeded_handler,
    )
