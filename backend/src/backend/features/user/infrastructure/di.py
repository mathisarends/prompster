from backend.env import RateLimitSettings
from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import AsyncSession

from backend.features.user.application import UserMessageRateLimitService, UserService
from backend.features.user.domain import (
    UserMessageRateLimitPolicy,
    UserMessageQuotaRepository,
    UserRepository,
)
from backend.features.user.infrastructure.repository import (
    SqlUserMessageQuotaRepository,
)


class UserProvider(Provider):
    @provide(scope=Scope.APP)
    def provide_rate_limit_settings(self) -> RateLimitSettings:
        return RateLimitSettings()

    @provide(scope=Scope.APP)
    def provide_user_message_quota_policy(
        self,
        settings: RateLimitSettings,
    ) -> UserMessageRateLimitPolicy:
        return UserMessageRateLimitPolicy(
            daily_message_limit=settings.agent_message_daily_limit
        )

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
        policy: UserMessageRateLimitPolicy,
    ) -> UserMessageRateLimitService:
        return UserMessageRateLimitService(
            quota_repository=quota_repository,
            policy=policy,
        )

    @provide(scope=Scope.REQUEST)
    def provide_user_service(
        self,
        user_repository: UserRepository,
    ) -> UserService:
        return UserService(user_repository=user_repository)
