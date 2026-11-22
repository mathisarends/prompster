from typing import NamedTuple
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.engine import Row
from sqlalchemy.ext.asyncio import AsyncSession

from backend.features.user.domain import (
    AuthIdentity,
    AuthProvider,
    SpotifyAccount,
    User,
    UserRepository,
)
from backend.platform.database import Repository
from backend.platform.database.orm import (
    AuthIdentityModel,
    OAuthConnectionModel,
    SessionModel,
    UserModel,
)
from backend.shared.oauth_provider import OAuthProvider


def _select_user_with_spotify_connection():
    return select(
        UserModel,
        OAuthConnectionModel.id,
        OAuthConnectionModel.is_premium,
    ).outerjoin(
        OAuthConnectionModel,
        and_(
            OAuthConnectionModel.user_id == UserModel.id,
            OAuthConnectionModel.provider == OAuthProvider.SPOTIFY,
        ),
    )


class _UserConnectionColumns(NamedTuple):
    user: UserModel
    oauth_connection_id: UUID | None
    is_premium: bool | None


def _split_user_with_connection(
    row: Row[_UserConnectionColumns],
) -> tuple[UserModel, SpotifyAccount]:
    user_orm, oauth_connection_id, is_premium = row[0], row[1], row[2]
    if oauth_connection_id is None:
        return user_orm, SpotifyAccount.disconnected()
    return user_orm, SpotifyAccount.connected_with(is_premium=bool(is_premium))


class SqlUserRepository(Repository[UserModel, User], UserRepository):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session=session, model=UserModel)

    async def get_by_id(self, *, user_id: UUID) -> User | None:
        stmt = _select_user_with_spotify_connection().where(UserModel.id == user_id)
        row = (await self.session.execute(stmt)).first()
        if row is None:
            return None

        user_orm, spotify = _split_user_with_connection(row)
        return self._to_domain(user_orm, spotify=spotify)

    async def delete_by_id(self, *, user_id: UUID) -> bool:
        return await super().delete_by_id(user_id)

    async def count_sessions_for_user(self, *, user_id: UUID) -> int:
        stmt = select(func.count(SessionModel.id)).where(
            SessionModel.owner_id == user_id
        )
        count = await self.session.scalar(stmt)
        return int(count or 0)

    async def get_by_auth_identity(
        self,
        *,
        provider: AuthProvider,
        subject: str,
    ) -> User | None:
        stmt = (
            _select_user_with_spotify_connection()
            .join(AuthIdentityModel, AuthIdentityModel.user_id == UserModel.id)
            .where(
                AuthIdentityModel.provider == provider.value,
                AuthIdentityModel.subject == subject,
            )
        )
        row = (await self.session.execute(stmt)).first()
        if row is None:
            return None

        user_orm, spotify = _split_user_with_connection(row)
        return self._to_domain(user_orm, spotify=spotify)

    async def create(self, *, user: User) -> User:
        return await self.save(user)

    async def update(self, *, user: User) -> User:
        return await self.save(user)

    async def create_with_auth_identity(
        self,
        *,
        user: User,
        auth_identity: AuthIdentity,
    ) -> User:
        user_orm = self._to_orm(user)
        self.session.add(user_orm)
        await self.session.flush()

        auth_identity_orm = AuthIdentityModel(
            id=auth_identity.id,
            user_id=auth_identity.user_id,
            provider=auth_identity.provider.value,
            subject=auth_identity.subject,
            created_at=auth_identity.created_at,
        )
        self.session.add(auth_identity_orm)
        await self.session.flush()
        await self.session.refresh(user_orm)
        return self._to_domain(user_orm)

    def _to_domain(
        self,
        orm: UserModel,
        *,
        spotify: SpotifyAccount | None = None,
    ) -> User:
        return User.restore(
            id=orm.id,
            created_at=orm.created_at,
            name=orm.name,
            profile_image_url=orm.profile_image_url,
            spotify=spotify if spotify is not None else SpotifyAccount.disconnected(),
        )

    def _to_orm(self, domain: User) -> UserModel:
        return UserModel(
            id=domain.id,
            name=domain.name,
            profile_image_url=domain.profile_image_url,
            created_at=domain.created_at,
        )
