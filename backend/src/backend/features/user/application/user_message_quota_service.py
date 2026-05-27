import hashlib
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from backend.features.user.domain import (
    UserMessageQuotaExceededError,
    UserMessageRateLimitPolicy,
    UserMessageQuotaRepository,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class UserMessageRateLimitSnapshot:
    limit: int
    remaining: int
    reset_at: datetime


class UserMessageRateLimitService:
    def __init__(
        self,
        quota_repository: UserMessageQuotaRepository,
        policy: UserMessageRateLimitPolicy,
    ) -> None:
        self._quota_repository = quota_repository
        self._policy = policy

    async def consume(self, *, user_id: UUID) -> None:
        quota = await self._quota_repository.get_or_create_for_update(user_id=user_id)
        try:
            quota.consume(policy=self._policy, now=datetime.now(timezone.utc))
        except UserMessageQuotaExceededError:
            logger.warning(
                "User message quota exceeded: user=%s limit=%d reset_at=%s",
                _hash_user_id(user_id),
                self._policy.daily_message_limit,
                quota.reset_at(policy=self._policy).isoformat(),
            )
            raise

        await self._quota_repository.save(quota=quota)

        remaining = quota.remaining(policy=self._policy)
        threshold = max(1, int(self._policy.daily_message_limit * 0.2))
        if remaining <= threshold:
            logger.info(
                "User message quota near limit: user=%s remaining=%d limit=%d",
                _hash_user_id(user_id),
                remaining,
                self._policy.daily_message_limit,
            )

    async def inspect(self, *, user_id: UUID) -> UserMessageRateLimitSnapshot:
        quota = await self._quota_repository.get_by_user_id(user_id=user_id)
        now = datetime.now(timezone.utc)
        if quota is None or quota.is_window_expired(policy=self._policy, now=now):
            return UserMessageRateLimitSnapshot(
                limit=self._policy.daily_message_limit,
                remaining=self._policy.daily_message_limit,
                reset_at=now + self._policy.window,
            )

        return UserMessageRateLimitSnapshot(
            limit=self._policy.daily_message_limit,
            remaining=quota.remaining(policy=self._policy),
            reset_at=quota.reset_at(policy=self._policy),
        )


def _hash_user_id(user_id: UUID) -> str:
    return hashlib.sha256(str(user_id).encode("utf-8")).hexdigest()[:12]
