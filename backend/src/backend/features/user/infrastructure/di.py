from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import AsyncSession

from backend.features.user.application import UserMessageQuotaService, UserService
from backend.features.user.domain import (
    UserMessageQuotaPolicy,
    UserMessageQuotaRepository,
    UserRepository,
)
from backend.features.user.infrastructure.repository import (
    SqlUserMessageQuotaRepository,
)
from backend.features.user.infrastructure.settings import UserMessageQuotaSettings


class UserProvider(Provider):
    @provide(scope=Scope.APP)
    def provide_user_message_quota_settings(self) -> UserMessageQuotaSettings:
        return UserMessageQuotaSettings()

    @provide(scope=Scope.APP)
    def provide_user_message_quota_policy(
        self,
        settings: UserMessageQuotaSettings,
    ) -> UserMessageQuotaPolicy:
        return UserMessageQuotaPolicy(daily_message_limit=settings.daily_message_limit)

    @provide(scope=Scope.REQUEST)
    def provide_user_message_quota_repository(
        self,
        session: AsyncSession,
    ) -> UserMessageQuotaRepository:
        return SqlUserMessageQuotaRepository(session=session)

    @provide(scope=Scope.REQUEST)
    def provide_user_message_quota_service(
        self,
        quota_repository: UserMessageQuotaRepository,
        policy: UserMessageQuotaPolicy,
    ) -> UserMessageQuotaService:
        return UserMessageQuotaService(quota_repository=quota_repository, policy=policy)

    @provide(scope=Scope.REQUEST)
    def provide_user_service(
        self,
        user_repository: UserRepository,
    ) -> UserService:
        return UserService(user_repository=user_repository)
