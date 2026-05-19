from typing import Annotated
from uuid import UUID

from dishka.integrations.fastapi import FromDishka
from fastapi import Depends, HTTPException, WebSocket, WebSocketException, status
from starlette.requests import HTTPConnection

from backend.features.auth.application.ports import TokenIssuer
from backend.features.auth.application.schemas import TokenPayload, TokenType
from backend.features.auth.infrastructure.auth_settings import AuthSettings


def _get_token_payload(
    conn: HTTPConnection,
    auth_settings: FromDishka[AuthSettings],
    token_issuer: FromDishka[TokenIssuer],
) -> TokenPayload:
    token = conn.cookies.get(auth_settings.access_token_cookie_name)
    if not token:
        _raise(conn, "Authentication required")

    try:
        return token_issuer.validate(token, expected_type=TokenType.ACCESS)
    except Exception as exc:
        _raise(conn, "Invalid or expired token", exc)


def _raise(conn: HTTPConnection, detail: str, exc: Exception | None = None) -> None:
    if isinstance(conn, WebSocket):
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason=detail,
        ) from exc

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
    ) from exc


def _get_authenticated_user_id(
    payload: Annotated[TokenPayload, Depends(_get_token_payload)],
) -> UUID:
    return payload.user_id


AuthenticatedUserId = Annotated[UUID, Depends(_get_authenticated_user_id)]
