import asyncio
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from backend.features.user.application import UserMessageQuotaService
from backend.features.user.domain import (
    UserMessageQuota,
    UserMessageQuotaPolicy,
    UserMessageQuotaRepository,
)


class _UserMessageQuotaRepositoryStub(UserMessageQuotaRepository):
    def __init__(self) -> None:
        self.quota_for_update: UserMessageQuota | None = None
        self.quota_for_read: UserMessageQuota | None = None
        self.saved_quota: UserMessageQuota | None = None
        self.received_for_update_user_id: UUID | None = None
        self.received_read_user_id: UUID | None = None

    async def get_or_create_for_update(self, *, user_id: UUID) -> UserMessageQuota:
        self.received_for_update_user_id = user_id
        assert self.quota_for_update is not None
        return self.quota_for_update

    async def get_by_user_id(self, *, user_id: UUID) -> UserMessageQuota | None:
        self.received_read_user_id = user_id
        return self.quota_for_read

    async def save(self, *, quota: UserMessageQuota) -> UserMessageQuota:
        self.saved_quota = quota
        return quota


class TestUserMessageQuotaService:
    def test_consume_increments_and_persists(self) -> None:
        user_id = uuid4()
        repository = _UserMessageQuotaRepositoryStub()
        repository.quota_for_update = UserMessageQuota.fresh(
            user_id=user_id,
            now=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        service = UserMessageQuotaService(
            quota_repository=repository,
            policy=UserMessageQuotaPolicy(daily_message_limit=50),
        )

        asyncio.run(service.consume(user_id=user_id))

        assert repository.received_for_update_user_id == user_id
        assert repository.saved_quota is repository.quota_for_update
        assert repository.saved_quota is not None
        assert repository.saved_quota.messages_consumed == 1

    def test_inspect_returns_full_limit_for_new_user(self) -> None:
        user_id = uuid4()
        repository = _UserMessageQuotaRepositoryStub()
        service = UserMessageQuotaService(
            quota_repository=repository,
            policy=UserMessageQuotaPolicy(daily_message_limit=50),
        )

        snapshot = asyncio.run(service.inspect(user_id=user_id))

        assert repository.received_read_user_id == user_id
        assert snapshot.limit == 50
        assert snapshot.remaining == 50
        assert snapshot.reset_at.tzinfo == timezone.utc

    def test_inspect_resets_remaining_for_expired_window(self) -> None:
        user_id = uuid4()
        now = datetime.now(timezone.utc)
        repository = _UserMessageQuotaRepositoryStub()
        repository.quota_for_read = UserMessageQuota(
            user_id=user_id,
            window_started_at=now - timedelta(days=2),
            messages_consumed=50,
        )
        service = UserMessageQuotaService(
            quota_repository=repository,
            policy=UserMessageQuotaPolicy(daily_message_limit=50),
        )

        snapshot = asyncio.run(service.inspect(user_id=user_id))

        assert snapshot.limit == 50
        assert snapshot.remaining == 50
