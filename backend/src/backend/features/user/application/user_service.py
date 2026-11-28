from dataclasses import dataclass
from uuid import UUID

from backend.features.user.domain import User, UserRepository
from backend.shared.authentication import SessionInvalidError


@dataclass(frozen=True, slots=True)
class UserDeleteInformation:
    session_count: int


class UserService:
    def __init__(self, user_repository: UserRepository) -> None:
        self._user_repository = user_repository

    async def get_me(self, *, user_id: UUID) -> User:
        user = await self._user_repository.get_by_id(user_id=user_id)
        if user is None:
            raise SessionInvalidError("Invalid user")
        return user

    async def delete_me(self, *, user_id: UUID) -> None:
        deleted = await self._user_repository.delete_by_id(user_id=user_id)
        if not deleted:
            raise SessionInvalidError("Invalid user")

    async def get_delete_information(self, *, user_id: UUID) -> UserDeleteInformation:
        user = await self._user_repository.get_by_id(user_id=user_id)
        if user is None:
            raise SessionInvalidError("Invalid user")

        session_count = await self._user_repository.count_sessions_for_user(
            user_id=user_id
        )
        return UserDeleteInformation(session_count=session_count)
