from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.engine import Row

from backend.features.oauth_connections.domain import OAuthProvider
from backend.features.user.domain import (
    AuthIdentity,
    AuthProvider,
    SpotifyAccount,
    User,
    UserMessageQuota,
    UserMessageQuotaRepository,
    UserRepository,
)
from backend.infrastructure.database.orm import (
    AuthIdentityModel,
    OAuthConnectionModel,
    SessionModel,
    UserMessageQuotaModel,
    UserModel,
)
from backend.infrastructure.database.repository import Repository


class SqlUserRepository(Repository[UserModel, User], UserRepository):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session=session, model=UserModel)

    def _to_domain(
        self,
        orm: UserModel,
        *,
        spotify: SpotifyAccount | None = None,
    ) -> User:
        return User(
            id=orm.id,
            name=orm.name,
            email=orm.email,
            profile_image_url=orm.profile_image_url,
            spotify=spotify or SpotifyAccount.disconnected(),
            created_time=orm.created_at,
        )

    def _to_orm(self, domain: User) -> UserModel:
        return UserModel(
            id=domain.id,
            name=domain.name,
            email=domain.email,
            profile_image_url=domain.profile_image_url,
            created_at=domain.created_at,
        )

    async def get_by_id(self, *, user_id: UUID) -> User | None:
        stmt = self._select_user_with_spotify_connection().where(
            UserModel.id == user_id
        )
        row = (await self.session.execute(stmt)).first()
        if row is None:
            return None

        user_orm, spotify = self._split_user_with_connection(row)
        return self._to_domain(user_orm, spotify=spotify)

    async def delete_by_id(self, *, user_id: UUID) -> bool:
        return await super().delete_by_id(user_id)

    async def count_sessions_for_user(self, *, user_id: UUID) -> int:
        stmt = select(func.count(SessionModel.id)).where(
            SessionModel.owner_id == user_id
        )
        count = await self.session.scalar(stmt)
        return int(count or 0)

    async def get_by_email(self, *, email: str) -> User | None:
        normalized_email = email.strip().lower()
        return await self.find_by(email=normalized_email)

    async def get_by_auth_identity(
        self,
        *,
        provider: AuthProvider,
        subject: str,
    ) -> User | None:
        stmt = (
            self._select_user_with_spotify_connection()
            .join(AuthIdentityModel, AuthIdentityModel.user_id == UserModel.id)
            .where(
                AuthIdentityModel.provider == provider.value,
                AuthIdentityModel.subject == subject,
            )
        )
        row = (await self.session.execute(stmt)).first()
        if row is None:
            return None

        user_orm, spotify = self._split_user_with_connection(row)
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

    @staticmethod
    def _select_user_with_spotify_connection():
        return select(
            UserModel,
            OAuthConnectionModel.id,
            OAuthConnectionModel.is_premium,
        ).outerjoin(
            OAuthConnectionModel,
            and_(
                OAuthConnectionModel.user_id == UserModel.id,
                OAuthConnectionModel.provider == OAuthProvider.SPOTIFY.value,
            ),
        )

    @staticmethod
    def _split_user_with_connection(
        row: Row[tuple[UserModel, UUID | None, bool | None]],
    ) -> tuple[UserModel, SpotifyAccount]:
        user_orm, oauth_connection_id, is_premium = row[0], row[1], row[2]
        if oauth_connection_id is None:
            return user_orm, SpotifyAccount.disconnected()
        return user_orm, SpotifyAccount.connected_with(is_premium=bool(is_premium))


class SqlUserMessageQuotaRepository(
    Repository[UserMessageQuotaModel, UserMessageQuota],
    UserMessageQuotaRepository,
):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session=session, model=UserMessageQuotaModel)

    def _to_domain(self, orm: UserMessageQuotaModel) -> UserMessageQuota:
        return UserMessageQuota(
            id=orm.id,
            created_time=orm.created_at,
            user_id=orm.user_id,
            window_started_at=orm.window_started_at,
            messages_consumed=orm.messages_consumed,
        )

    def _to_orm(self, domain: UserMessageQuota) -> UserMessageQuotaModel:
        return UserMessageQuotaModel(
            id=domain.id,
            created_at=domain.created_at,
            user_id=domain.user_id,
            window_started_at=domain.window_started_at,
            messages_consumed=domain.messages_consumed,
        )

    async def get_or_create_for_update(self, *, user_id: UUID) -> UserMessageQuota:
        stmt = self._select_by_user_id(user_id=user_id, with_for_update=True)
        orm = (await self.session.execute(stmt)).scalar_one_or_none()
        if orm is not None:
            return self._to_domain(orm)

        quota = UserMessageQuota.fresh(user_id=user_id)
        try:
            async with self.session.begin_nested():
                self.session.add(self._to_orm(quota))
                await self.session.flush()
        except IntegrityError:
            # Parallel first-write race: another request inserted the row.
            pass

        orm = (await self.session.execute(stmt)).scalar_one()
        return self._to_domain(orm)

    async def get_by_user_id(self, *, user_id: UUID) -> UserMessageQuota | None:
        stmt = self._select_by_user_id(user_id=user_id, with_for_update=False)
        orm = (await self.session.execute(stmt)).scalar_one_or_none()
        if orm is None:
            return None
        return self._to_domain(orm)

    async def save(self, *, quota: UserMessageQuota) -> UserMessageQuota:
        return await super().save(quota)

    @staticmethod
    def _select_by_user_id(*, user_id: UUID, with_for_update: bool):
        stmt = select(UserMessageQuotaModel).where(
            UserMessageQuotaModel.user_id == user_id
        )
        if with_for_update:
            stmt = stmt.with_for_update()
        return stmt
