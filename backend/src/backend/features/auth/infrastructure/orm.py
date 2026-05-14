from uuid import UUID

from backend.features.auth.domain import (
    AuthUser,
    AuthUserRepository,
    RefreshSession,
    RefreshSessionRepository,
)


class InMemoryAuthUserRepository(AuthUserRepository):
    def __init__(self) -> None:
        self._users_by_id: dict[UUID, AuthUser] = {}
        self._user_ids_by_email: dict[str, UUID] = {}

    async def get_by_id(self, *, user_id: UUID) -> AuthUser | None:
        return self._users_by_id.get(user_id)

    async def get_by_email(self, *, email: str) -> AuthUser | None:
        normalized_email = email.strip().lower()
        user_id = self._user_ids_by_email.get(normalized_email)
        if user_id is None:
            return None
        return self._users_by_id.get(user_id)

    async def create(self, *, user: AuthUser) -> AuthUser:
        normalized_email = user.email.strip().lower()
        if normalized_email in self._user_ids_by_email:
            raise ValueError("User already exists")

        self._users_by_id[user.id] = user
        self._user_ids_by_email[normalized_email] = user.id
        return user


class InMemoryRefreshSessionRepository(RefreshSessionRepository):
    def __init__(self) -> None:
        self._sessions_by_token: dict[str, RefreshSession] = {}

    async def get_by_token(self, *, token: str) -> RefreshSession | None:
        return self._sessions_by_token.get(token)

    async def save(self, *, refresh_session: RefreshSession) -> None:
        self._sessions_by_token[refresh_session.token] = refresh_session

    async def delete(self, *, token: str) -> None:
        self._sessions_by_token.pop(token, None)
