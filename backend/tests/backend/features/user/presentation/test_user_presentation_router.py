import asyncio
from datetime import datetime, timezone
from typing import cast
from uuid import UUID, uuid4

from backend.features.user.application import UserDeleteInformation
from backend.features.user.application import UserMessageRateLimitService
from backend.features.user.application import UserMessageRateLimitSnapshot
from backend.features.user.application import UserService
from backend.features.user.domain import SpotifyAccount, User
from backend.features.user.presentation.router import (
    delete_me,
    get_delete_information,
    get_me,
)


class _UserServiceStub:
    def __init__(self) -> None:
        self.received_get_me_user_id: UUID | None = None
        self.received_delete_user_id: UUID | None = None
        self.received_delete_information_user_id: UUID | None = None
        self.session_count = 0
        self.user = User(
            id=uuid4(),
            name="Mathis",
            spotify=SpotifyAccount.connected_with(is_premium=True),
            created_time=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )

    async def get_me(self, *, user_id: UUID):
        self.received_get_me_user_id = user_id
        return self.user

    async def delete_me(self, *, user_id: UUID) -> None:
        self.received_delete_user_id = user_id

    async def get_delete_information(self, *, user_id: UUID) -> UserDeleteInformation:
        self.received_delete_information_user_id = user_id
        return UserDeleteInformation(session_count=self.session_count)


class _UserMessageRateLimitServiceStub:
    def __init__(self) -> None:
        self.received_user_id: UUID | None = None
        self.snapshot = UserMessageRateLimitSnapshot(
            limit=50,
            remaining=49,
            reset_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
        )

    async def inspect(self, *, user_id: UUID) -> UserMessageRateLimitSnapshot:
        self.received_user_id = user_id
        return self.snapshot


class TestGetMeRoute:
    def test_get_me_returns_user_with_message_rate_limit(self) -> None:
        user_service = _UserServiceStub()
        rate_limit_service = _UserMessageRateLimitServiceStub()
        authenticated_user_id = uuid4()

        response = asyncio.run(
            get_me(
                authenticated_user_id=authenticated_user_id,
                service=cast(UserService, user_service),
                message_rate_limit_service=cast(
                    UserMessageRateLimitService,
                    rate_limit_service,
                ),
            )
        )

        assert response.id == user_service.user.id
        assert response.name == "Mathis"
        assert response.spotify_connected is True
        assert response.spotify_premium is True
        assert response.message_rate_limit.limit == 50
        assert response.message_rate_limit.remaining == 49
        assert response.message_rate_limit.reset_at == datetime(
            2026, 1, 2, tzinfo=timezone.utc
        )
        assert user_service.received_get_me_user_id == authenticated_user_id
        assert rate_limit_service.received_user_id == authenticated_user_id


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
