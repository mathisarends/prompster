from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.engine import Row

from backend.features.oauth_connections.domain import OAuthProvider
from backend.features.user.domain import User, UserRepository
from backend.infrastructure.database.orm import OAuthConnectionModel, UserModel
from backend.infrastructure.database.repository import Repository

from sqlalchemy.ext.asyncio import AsyncSession


class SqlUserRepository(Repository[UserModel, User], UserRepository):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session=session, model=UserModel)

    def _to_domain(self, orm: UserModel, *, spotify_connected: bool = False) -> User:
        return User(
            id=orm.id,
            name=orm.name,
            email=orm.email,
            google_subject=orm.google_subject,
            spotify_connected=spotify_connected,
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
        stmt = (
            select(UserModel, OAuthConnectionModel.id)
            .outerjoin(
                OAuthConnectionModel,
                and_(
                    OAuthConnectionModel.user_id == UserModel.id,
                    OAuthConnectionModel.provider == OAuthProvider.SPOTIFY.value,
                ),
            )
            .where(UserModel.id == user_id)
        )
        row = (await self.session.execute(stmt)).first()
        if row is None:
            return None

        user_orm, oauth_connection_id = self._split_user_with_connection(row)
        return self._to_domain(
            user_orm,
            spotify_connected=oauth_connection_id is not None,
        )

    async def get_by_email(self, *, email: str) -> User | None:
        normalized_email = email.strip().lower()
        return await self.find_by(email=normalized_email)

    async def create(self, *, user: User) -> User:
        return await self.save(user)

    @staticmethod
    def _split_user_with_connection(
        row: Row[tuple[UserModel, UUID | None]],
    ) -> tuple[UserModel, UUID | None]:
        return row[0], row[1]
