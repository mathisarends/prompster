from uuid import UUID

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from backend.features.oauth_connections.infrastructure.oauth_token_cipher import (
    OAuthTokenCipher,
)
from backend.features.oauth_connections.domain import (
    OAuthConnection,
    OAuthConnectionRepository,
    OAuthProvider,
)
from backend.infrastructure.database.orm import OAuthConnectionModel
from backend.infrastructure.database.repository import Repository


class SqlOAuthConnectionRepository(
    Repository[OAuthConnectionModel, OAuthConnection],
    OAuthConnectionRepository,
):
    def __init__(self, session: AsyncSession, token_cipher: OAuthTokenCipher) -> None:
        super().__init__(session=session, model=OAuthConnectionModel)
        self._token_cipher = token_cipher

    def _to_domain(self, orm: OAuthConnectionModel) -> OAuthConnection:
        return OAuthConnection(
            id=orm.id,
            created_time=orm.created_at,
            user_id=orm.user_id,
            provider=OAuthProvider(orm.provider),
            provider_user_id=orm.provider_user_id,
            refresh_token=self._token_cipher.decrypt(orm.refresh_token_encrypted),
            scope=orm.scope,
            connected_at=orm.connected_at,
            is_premium=orm.is_premium,
        )

    def _to_orm(self, domain: OAuthConnection) -> OAuthConnectionModel:
        return OAuthConnectionModel(
            id=domain.id,
            created_at=domain.created_at,
            user_id=domain.user_id,
            provider=domain.provider.value,
            provider_user_id=domain.provider_user_id,
            refresh_token_encrypted=self._token_cipher.encrypt(domain.refresh_token),
            scope=domain.scope,
            connected_at=domain.connected_at,
            is_premium=domain.is_premium,
        )

    async def get(
        self,
        *,
        user_id: UUID,
        provider: OAuthProvider,
    ) -> OAuthConnection | None:
        return await self.find_by(user_id=user_id, provider=provider.value)

    async def save(self, *, connection: OAuthConnection) -> OAuthConnection:
        return await super().save(connection)

    async def delete(self, *, user_id: UUID, provider: OAuthProvider) -> bool:
        stmt = delete(self.model).where(
            self.model.user_id == user_id,
            self.model.provider == provider.value,
        )
        result = await self.session.execute(stmt)
        return result.rowcount > 0

    async def exists(self, *, user_id: UUID, provider: OAuthProvider) -> bool:
        return await super().exists(user_id=user_id, provider=provider.value)
