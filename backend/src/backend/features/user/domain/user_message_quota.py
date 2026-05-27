from datetime import datetime, timezone
from typing import Self
from uuid import UUID

from backend.features.user.domain.exceptions import UserMessageQuotaExceededError
from backend.features.user.domain.user_message_quota_policy import (
    UserMessageQuotaPolicy,
)
from backend.shared.ddd import Aggregate


class UserMessageQuota(Aggregate):
    def __init__(
        self,
        *,
        user_id: UUID,
        window_started_at: datetime,
        messages_consumed: int,
        id: UUID | None = None,
        created_time: datetime | None = None,
    ) -> None:
        super().__init__(id=id, created_time=created_time)
        self.user_id = user_id
        self.window_started_at = window_started_at
        self.messages_consumed = messages_consumed

    @classmethod
    def fresh(
        cls,
        *,
        user_id: UUID,
        now: datetime | None = None,
    ) -> Self:
        now = now or datetime.now(timezone.utc)
        return cls(
            user_id=user_id,
            window_started_at=now,
            messages_consumed=0,
        )

    def reset_at(self, *, policy: UserMessageQuotaPolicy) -> datetime:
        return self.window_started_at + policy.window

    def remaining(self, *, policy: UserMessageQuotaPolicy) -> int:
        return max(0, policy.daily_message_limit - self.messages_consumed)

    def is_window_expired(
        self,
        *,
        policy: UserMessageQuotaPolicy,
        now: datetime,
    ) -> bool:
        return now >= self.reset_at(policy=policy)

    def consume(
        self,
        *,
        policy: UserMessageQuotaPolicy,
        now: datetime,
    ) -> None:
        if self.is_window_expired(policy=policy, now=now):
            self.window_started_at = now
            self.messages_consumed = 0

        if self.messages_consumed >= policy.daily_message_limit:
            raise UserMessageQuotaExceededError(
                limit=policy.daily_message_limit,
                reset_at=self.reset_at(policy=policy),
            )

        self.messages_consumed += 1
