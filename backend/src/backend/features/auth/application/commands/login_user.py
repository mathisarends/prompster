from datetime import UTC, datetime, timedelta

from backend.features.auth.application.exceptions import InvalidCredentialsException
from backend.features.auth.application.ports import PasswordHasher, TokenGenerator
from backend.features.auth.application.schemas import AuthSession
from backend.features.auth.domain import (
    AuthUserRepository,
    RefreshSession,
    RefreshSessionRepository,
)


class LoginUserHandler:
    def __init__(
        self,
        user_repository: AuthUserRepository,
        refresh_session_repository: RefreshSessionRepository,
        password_hasher: PasswordHasher,
        token_generator: TokenGenerator,
        refresh_token_expire_days: int,
    ) -> None:
        self._user_repository = user_repository
        self._refresh_session_repository = refresh_session_repository
        self._password_hasher = password_hasher
        self._token_generator = token_generator
        self._refresh_token_expire_days = refresh_token_expire_days

    async def handle(self, *, email: str, password: str) -> AuthSession:
        normalized_email = email.strip().lower()
        user = await self._user_repository.get_by_email(email=normalized_email)

        if user is None:
            raise InvalidCredentialsException("Invalid email or password")

        if not self._password_hasher.verify_password(
            plain_password=password,
            password_hash=user.password_hash,
        ):
            raise InvalidCredentialsException("Invalid email or password")

        refresh_token = self._token_generator.create_refresh_token()
        await self._refresh_session_repository.save(
            refresh_session=RefreshSession(
                token=refresh_token,
                user_id=user.id,
                expires_at=datetime.now(UTC)
                + timedelta(days=self._refresh_token_expire_days),
            )
        )

        return AuthSession(
            jwt_token=self._token_generator.create_access_token(user_id=user.id),
            refresh_token=refresh_token,
        )
