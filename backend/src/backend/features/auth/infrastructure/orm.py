from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import Field

from backend.features.user.domain import User, UserRepository
from backend.infrastructure.database.orm import DatabaseEntity
from backend.infrastructure.database.repository import Repository


class UserEntity(DatabaseEntity, table=True):
    __tablename__ = "users"

    name: str
    email: str = Field(index=True, unique=True)
    google_subject: str = Field(index=True, unique=True)


class SqlUserRepository(Repository[UserEntity, User], UserRepository):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session=session, model=UserEntity)

    def _to_domain(self, orm: UserEntity) -> User:
        return User(
            id=orm.id,
            name=orm.name,
            email=orm.email,
            google_subject=orm.google_subject,
            created_time=orm.created_at,
        )

    def _to_orm(self, domain: User) -> UserEntity:
        return UserEntity(
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
