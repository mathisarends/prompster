from datetime import UTC, datetime

from backend.features.auth.presentation.exceptions import AUTH_ERRORS
from backend.features.user.domain import UserMessageQuotaExceededError
from fastapi import status
from fastapi_canon import Error, ErrorRegistry
from pydantic import BaseModel


class MessageQuotaExtensions(BaseModel):
    limit: int
    remaining: int
    reset_at: datetime


def _quota_extensions(
    exception: UserMessageQuotaExceededError,
) -> MessageQuotaExtensions:
    return MessageQuotaExtensions(
        limit=exception.limit,
        remaining=0,
        reset_at=exception.reset_at,
    )


def _quota_headers(exception: UserMessageQuotaExceededError) -> dict[str, str]:
    retry_after = max(
        1,
        int((exception.reset_at - datetime.now(UTC)).total_seconds()),
    )
    return {"Retry-After": str(retry_after)}


USER_MESSAGE_QUOTA_EXCEEDED_ERROR = Error(
    UserMessageQuotaExceededError,
    status=status.HTTP_429_TOO_MANY_REQUESTS,
    code="user_message_quota_exceeded",
    title="User message quota exceeded",
    extensions_model=MessageQuotaExtensions,
    extensions=_quota_extensions,
    headers=_quota_headers,
    openapi_headers={
        "Retry-After": {
            "description": "Seconds until the message quota resets.",
            "schema": {"type": "integer", "minimum": 1},
        }
    },
)

USER_ERRORS = ErrorRegistry.merge(
    AUTH_ERRORS,
    ErrorRegistry(
        name="user_domain",
        errors=(USER_MESSAGE_QUOTA_EXCEEDED_ERROR,),
    ),
    name="user",
)
