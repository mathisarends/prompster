from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
import pytest

from backend.features.auth.infrastructure.auth_settings import AuthSettings
from backend.features.auth.infrastructure.jwt_token_issuer import JwtTokenIssuer
from backend.shared.authentication import (
    SessionExpiredException,
    SessionInvalidException,
    TokenType,
)

_TEST_TIME = datetime(2024, 1, 1, tzinfo=UTC)


class TestJwtTokenIssuer:
    @staticmethod
    def _issuer() -> JwtTokenIssuer:
        return JwtTokenIssuer(
            AuthSettings(
                jwt_secret="test-signing-secret-with-at-least-32-bytes",
                jwt_access_token_expire_minutes=15,
                jwt_refresh_token_expire_days=14,
                _env_file=None,
            )
        )

    def test_creates_and_validates_access_and_refresh_tokens(self) -> None:
        issuer = self._issuer()
        user_id = UUID(int=1)

        session = issuer.create_session(user_id)

        assert issuer.validate(session.access_token).user_id == user_id
        assert (
            issuer.validate(
                session.refresh_token,
                expected_type=TokenType.REFRESH,
            ).user_id
            == user_id
        )

    def test_rejects_token_with_unexpected_type(self) -> None:
        issuer = self._issuer()

        access_token = issuer.create_session(UUID(int=2)).access_token

        with pytest.raises(
            SessionInvalidException, match="Expected token type 'refresh'"
        ):
            issuer.validate(access_token, expected_type=TokenType.REFRESH)

    def test_translates_expired_and_malformed_jwt_errors(self) -> None:
        issuer = self._issuer()
        expired_token = jwt.encode(
            {
                "sub": str(UUID(int=3)),
                "iat": _TEST_TIME,
                "exp": _TEST_TIME - timedelta(seconds=1),
                "type": TokenType.ACCESS.value,
            },
            "test-signing-secret-with-at-least-32-bytes",
            algorithm="HS256",
        )

        with pytest.raises(SessionExpiredException, match="expired"):
            issuer.validate(expired_token)

        with pytest.raises(SessionInvalidException, match="Invalid token"):
            issuer.validate("not-a-jwt")

    @pytest.mark.parametrize(
        ("payload", "message"),
        [
            ({"type": "access", "exp": 1}, "missing subject"),
            (
                {"type": "access", "sub": "not-a-uuid", "exp": 1},
                "not a valid UUID",
            ),
            (
                {"type": "access", "sub": str(UUID(int=4)), "exp": "tomorrow"},
                "expiration claim is invalid",
            ),
        ],
    )
    def test_rejects_invalid_claims(
        self,
        monkeypatch: pytest.MonkeyPatch,
        payload: dict[str, str | int],
        message: str,
    ) -> None:
        issuer = self._issuer()
        monkeypatch.setattr(issuer, "_jwt_decode", lambda _token: payload)

        with pytest.raises(SessionInvalidException, match=message):
            issuer.validate("decoded-by-stub")
