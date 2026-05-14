from uuid import UUID

from backend.features.auth.application.exceptions import SessionInvalidException
from backend.features.auth.application.ports import TokenIssuer
from backend.features.auth.application.schemas import AuthSession
from backend.features.auth.domain import AuthUserRepository


class RefreshSessionHandler:
    def __init__(
        self,
        user_repository: AuthUserRepository,
        token_issuer: TokenIssuer,
    ) -> None:
        self._user_repository = user_repository
        self._token_issuer = token_issuer

    async def handle(self, *, user_id: UUID) -> AuthSession:
        user = await self._user_repository.get_by_id(user_id=user_id)
        if user is None:
            raise SessionInvalidException("Invalid user")

        return self._token_issuer.create_session(user_id=user.id)
