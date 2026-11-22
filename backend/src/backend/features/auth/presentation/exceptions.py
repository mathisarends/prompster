from fastapi import status
from fastapi_canon import Error

from backend.features.auth.domain import InvalidCredentialsException
from backend.presentation.authentication import AUTHENTICATION_REQUIRED_ERROR
from backend.shared.authentication import (
    SessionExpiredException,
    SessionInvalidException,
)

INVALID_CREDENTIALS_ERROR = Error(
    InvalidCredentialsException,
    status=status.HTTP_401_UNAUTHORIZED,
    code="invalid_credentials",
)
SESSION_EXPIRED_ERROR = Error(
    SessionExpiredException,
    status=status.HTTP_401_UNAUTHORIZED,
    code="session_expired",
)
SESSION_INVALID_ERROR = Error(
    SessionInvalidException,
    status=status.HTTP_401_UNAUTHORIZED,
    code="session_invalid",
    title="Invalid session",
)

AUTH_ERRORS = (
    AUTHENTICATION_REQUIRED_ERROR,
    INVALID_CREDENTIALS_ERROR,
    SESSION_EXPIRED_ERROR,
    SESSION_INVALID_ERROR,
)
