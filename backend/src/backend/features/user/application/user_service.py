from uuid import UUID

from backend.features.auth.application.exceptions import SessionInvalidException
from backend.features.oauth_connections.domain import (
    OAuthConnectionRepository,
    OAuthProvider,
)
from backend.features.user.application.schemas import UserMeDto
from backend.features.user.domain import User, UserRepository


class UserService:
    def __init__(
        self,
        user_repository: UserRepository,
        oauth_connection_repository: OAuthConnectionRepository,
    ) -> None:
        self._user_repository = user_repository
        self._oauth_connection_repository = oauth_connection_repository

    async def get_me(self, *, user_id: UUID) -> UserMeDto:
        user = await self._user_repository.get_by_id(user_id=user_id)
        if user is None:
            raise SessionInvalidException("Invalid user")

        spotify_connected = await self._oauth_connection_repository.exists(
            user_id=user_id,
            provider=OAuthProvider.SPOTIFY,
        )
        return UserMeDto(user=user, spotify_connected=spotify_connected)
