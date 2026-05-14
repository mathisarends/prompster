from datetime import UTC, datetime, timedelta

from backend.features.auth.application.exceptions import (
    SessionExpiredException,
    SessionInvalidException,
)
from backend.features.auth.application.ports import TokenGenerator
from backend.features.auth.application.schemas import AuthSession
from backend.features.auth.domain import (
    AuthUserRepository,
    RefreshSession,
    RefreshSessionRepository,
)


class RefreshSessionHandler:
    def __init__(
        self,
        user_repository: AuthUserRepository,
        refresh_session_repository: RefreshSessionRepository,
        token_generator: TokenGenerator,
        refresh_token_expire_days: int,
    ) -> None:
        self._user_repository = user_repository
        self._refresh_session_repository = refresh_session_repository
        self._token_generator = token_generator
        self._refresh_token_expire_days = refresh_token_expire_days

    async def handle(self, *, refresh_token: str) -> AuthSession:
        current_session = await self._refresh_session_repository.get_by_token(
            token=refresh_token
        )
        if current_session is None:
            raise SessionInvalidException("Invalid refresh token")

        if current_session.expires_at <= datetime.now(UTC):
            await self._refresh_session_repository.delete(token=refresh_token)
            raise SessionExpiredException("Refresh token expired")

        user = await self._user_repository.get_by_id(user_id=current_session.user_id)
        if user is None:
            await self._refresh_session_repository.delete(token=refresh_token)
            raise SessionInvalidException("Invalid refresh token")

        await self._refresh_session_repository.delete(token=refresh_token)

        new_refresh_token = self._token_generator.create_refresh_token()
        await self._refresh_session_repository.save(
            refresh_session=RefreshSession(
                token=new_refresh_token,
                user_id=user.id,
                expires_at=datetime.now(UTC)
                + timedelta(days=self._refresh_token_expire_days),
            )
        )

        return AuthSession(
            jwt_token=self._token_generator.create_access_token(user_id=user.id),
            refresh_token=new_refresh_token,
        )
