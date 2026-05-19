from uuid import UUID

from backend.features.user.domain import User, UserRepository
from backend.infrastructure.database.orm import UserModel
from backend.infrastructure.database.repository import Repository

from sqlalchemy.ext.asyncio import AsyncSession


class SqlUserRepository(Repository[UserModel, User], UserRepository):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session=session, model=UserModel)

    def _to_domain(self, orm: UserModel) -> User:
        return User(
            id=orm.id,
            name=orm.name,
            email=orm.email,
            google_subject=orm.google_subject,
            created_time=orm.created_at,
        )

    def _to_orm(self, domain: User) -> UserModel:
        return UserModel(
            id=domain.id,
            name=domain.name,
            email=domain.email,
            google_subject=domain.google_subject,
            created_at=domain.created_at,
        )

    async def get_by_id(self, *, user_id: UUID) -> User | None:
        return await self.find_by_id(user_id)

    async def get_by_email(self, *, email: str) -> User | None:
        normalized_email = email.strip().lower()
        return await self.find_by(email=normalized_email)

    async def create(self, *, user: User) -> User:
        return await self.save(user)
