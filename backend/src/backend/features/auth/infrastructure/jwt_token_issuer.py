from datetime import UTC, datetime, timedelta
from typing import TypedDict
from uuid import UUID

import jwt

from backend.shared.authentication import (
    AuthSession,
    SessionExpiredException,
    SessionInvalidException,
    TokenIssuer,
    TokenPayload,
    TokenType,
)
from backend.features.auth.infrastructure.auth_settings import AuthSettings


class _JwtPayload(TypedDict):
    sub: str
    iat: int | float
    exp: int | float
    type: str


class JwtTokenIssuer(TokenIssuer):
    def __init__(self, auth_settings: AuthSettings) -> None:
        self._config = auth_settings

    def create_session(self, user_id: UUID) -> AuthSession:
        now = datetime.now(UTC)
        access_token = self._encode(
            user_id,
            now,
            now + timedelta(minutes=self._config.jwt_access_token_expire_minutes),
            token_type=TokenType.ACCESS,
        )
        refresh_token = self._encode(
            user_id,
            now,
            now + timedelta(days=self._config.jwt_refresh_token_expire_days),
            token_type=TokenType.REFRESH,
        )

        return AuthSession(access_token=access_token, refresh_token=refresh_token)

    def validate(
        self,
        token: str,
        expected_type: TokenType = TokenType.ACCESS,
    ) -> TokenPayload:
        raw = self._jwt_decode(token)
        if raw.get("type") != expected_type.value:
            raise SessionInvalidException(
                f"Expected token type '{expected_type.value}'"
            )
        return self._parse_payload(raw)

    def _encode(
        self,
        user_id: UUID,
        iat: datetime,
        exp: datetime,
        token_type: TokenType,
    ) -> str:
        return jwt.encode(
            {
                "sub": str(user_id),
                "iat": iat,
                "exp": exp,
                "type": token_type.value,
            },
            self._config.jwt_secret,
            algorithm=self._config.jwt_algorithm,
        )

    def _jwt_decode(self, token: str) -> _JwtPayload:
        try:
            return jwt.decode(
                token,
                self._config.jwt_secret,
                algorithms=[self._config.jwt_algorithm],
            )
        except jwt.ExpiredSignatureError as exc:
            raise SessionExpiredException("Token has expired") from exc
        except jwt.InvalidTokenError as exc:
            raise SessionInvalidException(f"Invalid token: {exc}") from exc

    def _parse_payload(self, payload: _JwtPayload) -> TokenPayload:
        user_id_str = payload.get("sub")

        if not user_id_str:
            raise SessionInvalidException("Token is missing subject claim")

        try:
            user_id = UUID(user_id_str)
        except ValueError as exc:
            raise SessionInvalidException("Token subject is not a valid UUID") from exc

        exp_raw = payload.get("exp")
        if not isinstance(exp_raw, (int, float)):
            raise SessionInvalidException("Token expiration claim is invalid")

        return TokenPayload(
            user_id=user_id,
            expires_at=datetime.fromtimestamp(exp_raw, tz=UTC),
        )
