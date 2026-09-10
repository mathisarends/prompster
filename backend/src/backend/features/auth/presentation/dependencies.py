from typing import Annotated
from uuid import UUID

from backend.features.auth.application import (
    SessionExpiredException,
    SessionInvalidException,
)
from backend.features.auth.application.ports import TokenIssuer
from backend.features.auth.application.schemas import TokenPayload, TokenType
from backend.features.auth.infrastructure.auth_settings import AuthSettings
from backend.features.auth.presentation.exceptions import AuthenticationRequiredError
from fastapi import Depends, WebSocket, WebSocketException, status
from starlette.requests import HTTPConnection


async def _get_auth_settings(conn: HTTPConnection) -> AuthSettings:
    return await conn.state.dishka_container.get(AuthSettings)


async def _get_token_issuer(conn: HTTPConnection) -> TokenIssuer:
    return await conn.state.dishka_container.get(TokenIssuer)


def _get_cookie_token_payload(
    conn: HTTPConnection,
    auth_settings: AuthSettings,
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
    auth_settings: Annotated[AuthSettings, Depends(_get_auth_settings)],
    token_issuer: Annotated[TokenIssuer, Depends(_get_token_issuer)],
) -> TokenPayload:
    return _get_cookie_token_payload(
        conn,
        auth_settings,
        token_issuer,
        cookie_name=auth_settings.access_token_cookie_name,
        expected_type=TokenType.ACCESS,
    )


def _get_refresh_token_payload(
    conn: HTTPConnection,
    auth_settings: Annotated[AuthSettings, Depends(_get_auth_settings)],
    token_issuer: Annotated[TokenIssuer, Depends(_get_token_issuer)],
) -> TokenPayload:
    return _get_cookie_token_payload(
        conn,
        auth_settings,
        token_issuer,
        cookie_name=auth_settings.jwt_refresh_token_cookie_name,
        expected_type=TokenType.REFRESH,
    )


def _raise(conn: HTTPConnection, detail: str, exc: Exception | None = None) -> None:
    if isinstance(conn, WebSocket):
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason=detail,
        ) from exc

    raise AuthenticationRequiredError from exc


def _get_authenticated_user_id(
    payload: Annotated[TokenPayload, Depends(_get_access_token_payload)],
) -> UUID:
    return payload.user_id


def _get_refresh_authenticated_user_id(
    payload: Annotated[TokenPayload, Depends(_get_refresh_token_payload)],
) -> UUID:
    return payload.user_id


AuthenticatedUserId = Annotated[UUID, Depends(_get_authenticated_user_id)]
RefreshAuthenticatedUserId = Annotated[
    UUID,
    Depends(_get_refresh_authenticated_user_id),
]
