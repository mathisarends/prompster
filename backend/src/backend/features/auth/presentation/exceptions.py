from backend.features.auth.application import (
    InvalidCredentialsException,
    SessionExpiredException,
    SessionInvalidException,
)
from fastapi import status
from fastapi_canon import Error


class AuthenticationRequiredError(Exception):
    """Raised when an HTTP request has no usable authentication session."""


AUTHENTICATION_REQUIRED_ERROR = Error(
    AuthenticationRequiredError,
    status=status.HTTP_401_UNAUTHORIZED,
    code="authentication_required",
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
