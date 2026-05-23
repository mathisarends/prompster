from uuid import UUID

from backend.features.auth.application.exceptions import SessionInvalidException
from backend.features.user.domain import User, UserRepository


class UserService:
    def __init__(self, user_repository: UserRepository) -> None:
        self._user_repository = user_repository

    async def get_me(self, *, user_id: UUID) -> User:
        user = await self._user_repository.get_by_id(user_id=user_id)
        if user is None:
            raise SessionInvalidException("Invalid user")
        return user

    async def delete_me(self, *, user_id: UUID) -> None:
        deleted = await self._user_repository.delete_by_id(user_id=user_id)
        if not deleted:
            raise SessionInvalidException("Invalid user")
