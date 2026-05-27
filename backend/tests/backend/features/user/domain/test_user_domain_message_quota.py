from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from backend.features.user.domain import (
    UserMessageQuota,
    UserMessageQuotaExceededError,
    UserMessageQuotaPolicy,
)


class TestUserMessageQuotaPolicy:
    def test_rejects_non_positive_daily_limit(self) -> None:
        with pytest.raises(ValueError, match="daily_message_limit must be positive"):
            UserMessageQuotaPolicy(daily_message_limit=0)


class TestUserMessageQuota:
    def test_consume_increments_messages_consumed(self) -> None:
        user_id = uuid4()
        policy = UserMessageQuotaPolicy(daily_message_limit=3)
        quota = UserMessageQuota.fresh(
            user_id=user_id,
            now=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )

        quota.consume(policy=policy, now=datetime(2026, 1, 1, tzinfo=timezone.utc))

        assert quota.messages_consumed == 1
        assert quota.remaining(policy=policy) == 2

    def test_consume_raises_when_limit_is_reached(self) -> None:
        user_id = uuid4()
        now = datetime(2026, 1, 1, tzinfo=timezone.utc)
        policy = UserMessageQuotaPolicy(daily_message_limit=1)
        quota = UserMessageQuota(
            user_id=user_id,
            window_started_at=now,
            messages_consumed=1,
        )

        with pytest.raises(UserMessageQuotaExceededError) as exc_info:
            quota.consume(policy=policy, now=now)

        assert exc_info.value.limit == 1
        assert exc_info.value.reset_at == now + timedelta(hours=24)

    def test_consume_resets_expired_window_before_increment(self) -> None:
        user_id = uuid4()
        started_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
        now = datetime(2026, 1, 2, tzinfo=timezone.utc)
        policy = UserMessageQuotaPolicy(daily_message_limit=5)
        quota = UserMessageQuota(
            user_id=user_id,
            window_started_at=started_at,
            messages_consumed=5,
        )

        quota.consume(policy=policy, now=now)

        assert quota.window_started_at == now
        assert quota.messages_consumed == 1
        assert quota.reset_at(policy=policy) == now + timedelta(hours=24)
