from fastapi import status
from fastapi_canon import Error

from backend.features.auth.domain import InvalidCredentialsError
from backend.presentation import AUTHENTICATION_REQUIRED_ERROR
from backend.shared.authentication import (
    SessionExpiredError,
    SessionInvalidError,
)

_INVALID_CREDENTIALS_ERROR = Error(
    InvalidCredentialsError,
    status=status.HTTP_401_UNAUTHORIZED,
    code="invalid_credentials",
)
SESSION_EXPIRED_ERROR = Error(
    SessionExpiredError,
    status=status.HTTP_401_UNAUTHORIZED,
    code="session_expired",
)
SESSION_INVALID_ERROR = Error(
    SessionInvalidError,
    status=status.HTTP_401_UNAUTHORIZED,
    code="session_invalid",
    title="Invalid session",
)

AUTH_ERRORS = (
    AUTHENTICATION_REQUIRED_ERROR,
    _INVALID_CREDENTIALS_ERROR,
    SESSION_EXPIRED_ERROR,
    SESSION_INVALID_ERROR,
)
