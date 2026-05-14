from uuid import UUID

from backend.features.auth.application.exceptions import (
    SessionExpiredException,
    SessionInvalidException,
)
from backend.features.auth.application.schemas import TokenType
from backend.features.auth.domain import AuthUser
from backend.features.auth.infrastructure import AuthSettings
from backend.features.auth.infrastructure.jwt_token_issuer import JwtTokenIssuer
from backend.features.user.domain import User


def extract_user_id(token: str, *, auth_settings: AuthSettings) -> UUID | None:
    token_issuer = JwtTokenIssuer(auth_settings=auth_settings)

    try:
        payload = token_issuer.validate(token, expected_type=TokenType.ACCESS)
    except (SessionExpiredException, SessionInvalidException):
        return None

    return payload.user_id


def to_user(auth_user: AuthUser) -> User:
    return User(
        id=auth_user.id,
        name=auth_user.name,
        email=auth_user.email,
        created_time=auth_user.created_at,
    )
