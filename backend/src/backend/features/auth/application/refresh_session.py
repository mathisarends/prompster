from uuid import UUID

from backend.features.user.domain import UserRepository
from backend.shared.authentication import (
    AuthSession,
    SessionInvalidException,
    TokenIssuer,
)


class SessionRefresher:
    def __init__(
        self,
        user_repository: UserRepository,
        token_issuer: TokenIssuer,
    ) -> None:
        self._user_repository = user_repository
        self._token_issuer = token_issuer

    async def refresh(self, *, user_id: UUID) -> AuthSession:
        user = await self._user_repository.get_by_id(user_id=user_id)
        if user is None:
            raise SessionInvalidException("Invalid user")

        return self._token_issuer.create_session(user_id=user.id)
