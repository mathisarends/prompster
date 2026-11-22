from dataclasses import dataclass
from typing import Annotated, Literal
from uuid import UUID

from fastapi import Depends, WebSocket, WebSocketException, status
from fastapi_canon import Error, Inject
from starlette.requests import HTTPConnection

from backend.shared.authentication import (
    SessionExpiredException,
    SessionInvalidException,
    TokenIssuer,
    TokenPayload,
    TokenType,
)


class AuthenticationRequiredError(Exception):
    """Raised when an HTTP request has no usable authentication session."""


AUTHENTICATION_REQUIRED_ERROR = Error(
    AuthenticationRequiredError,
    status=status.HTTP_401_UNAUTHORIZED,
    code="authentication_required",
)


@dataclass(frozen=True, slots=True)
class AuthCookieSettings:
    access_token_name: str
    refresh_token_name: str
    access_token_max_age_seconds: int
    refresh_token_max_age_seconds: int
    same_site_dev: Literal["lax", "strict", "none"]
    same_site_prod: Literal["lax", "strict", "none"]


def _get_cookie_token_payload(
    conn: HTTPConnection,
    token_issuer: TokenIssuer,
    *,
    cookie_name: str,
    expected_type: TokenType,
) -> TokenPayload:
    token = conn.cookies.get(cookie_name)
    if not token:
        _raise(conn, "Authentication required")

    try:
        return token_issuer.validate(token, expected_type=expected_type)
    except (SessionExpiredException, SessionInvalidException) as exc:
        _raise(conn, "Invalid or expired token", exc)


def _get_access_token_payload(
    conn: HTTPConnection,
    cookie_settings: Inject[AuthCookieSettings],
    token_issuer: Inject[TokenIssuer],
) -> TokenPayload:
    return _get_cookie_token_payload(
        conn,
        token_issuer,
        cookie_name=cookie_settings.access_token_name,
        expected_type=TokenType.ACCESS,
    )


def _get_refresh_token_payload(
    conn: HTTPConnection,
    cookie_settings: Inject[AuthCookieSettings],
    token_issuer: Inject[TokenIssuer],
) -> TokenPayload:
    return _get_cookie_token_payload(
        conn,
        token_issuer,
        cookie_name=cookie_settings.refresh_token_name,
        expected_type=TokenType.REFRESH,
    )


def _raise(conn: HTTPConnection, detail: str, exc: Exception | None = None) -> None:
    if isinstance(conn, WebSocket):
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason=detail,
        ) from exc

    raise AuthenticationRequiredError from exc


def get_authenticated_user_id(
    payload: Annotated[TokenPayload, Depends(_get_access_token_payload)],
) -> UUID:
    return payload.user_id


def _get_refresh_authenticated_user_id(
    payload: Annotated[TokenPayload, Depends(_get_refresh_token_payload)],
) -> UUID:
    return payload.user_id


AuthenticatedUserId = Annotated[UUID, Depends(get_authenticated_user_id)]
RefreshAuthenticatedUserId = Annotated[
    UUID,
    Depends(_get_refresh_authenticated_user_id),
]
