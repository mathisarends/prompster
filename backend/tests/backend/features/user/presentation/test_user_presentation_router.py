import asyncio
from datetime import datetime, timezone
from typing import cast
from uuid import UUID, uuid4

from backend.features.user.application import UserDeleteInformation
from backend.features.user.application import UserMessageQuotaSnapshot
from backend.features.user.application import UserMessageQuotaService
from backend.features.user.application import UserService
from backend.features.user.presentation.router import (
    delete_me,
    get_delete_information,
    get_my_message_quota,
)


class _UserServiceStub:
    def __init__(self) -> None:
        self.received_delete_user_id: UUID | None = None
        self.received_delete_information_user_id: UUID | None = None
        self.session_count = 0

    async def get_me(self, *, user_id: UUID):
        raise AssertionError("delete_me route must not call get_me")

    async def delete_me(self, *, user_id: UUID) -> None:
        self.received_delete_user_id = user_id

    async def get_delete_information(self, *, user_id: UUID) -> UserDeleteInformation:
        self.received_delete_information_user_id = user_id
        return UserDeleteInformation(session_count=self.session_count)


class _UserMessageQuotaServiceStub:
    def __init__(self) -> None:
        self.received_user_id: UUID | None = None
        self.snapshot = UserMessageQuotaSnapshot(
            limit=50,
            remaining=49,
            reset_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
        )

    async def inspect(self, *, user_id: UUID) -> UserMessageQuotaSnapshot:
        self.received_user_id = user_id
        return self.snapshot


class TestDeleteMeRoute:
    def test_delete_me_calls_service_with_authenticated_user_id(self) -> None:
        service = _UserServiceStub()
        authenticated_user_id = uuid4()

        response = asyncio.run(
            delete_me(
                authenticated_user_id=authenticated_user_id,
                service=cast(UserService, service),
            )
        )

        assert response.status_code == 204
        assert service.received_delete_user_id == authenticated_user_id


class TestGetDeleteInformationRoute:
    def test_get_delete_information_returns_minimal_session_count(self) -> None:
        service = _UserServiceStub()
        service.session_count = 5
        authenticated_user_id = uuid4()

        response = asyncio.run(
            get_delete_information(
                authenticated_user_id=authenticated_user_id,
                service=cast(UserService, service),
            )
        )

        assert response.session_count == 5
        assert service.received_delete_information_user_id == authenticated_user_id


class TestGetMyMessageQuotaRoute:
    def test_get_my_message_quota_returns_snapshot_for_authenticated_user(self) -> None:
        service = _UserMessageQuotaServiceStub()
        authenticated_user_id = uuid4()

        response = asyncio.run(
            get_my_message_quota(
                authenticated_user_id=authenticated_user_id,
                service=cast(UserMessageQuotaService, service),
            )
        )

        assert response.limit == 50
        assert response.remaining == 49
        assert response.reset_at == datetime(2026, 1, 2, tzinfo=timezone.utc)
        assert service.received_user_id == authenticated_user_id
