import asyncio
from typing import cast
from uuid import UUID, uuid4

from backend.features.user.application import UserService
from backend.features.user.presentation.router import delete_me


class _UserServiceStub:
    def __init__(self) -> None:
        self.received_delete_user_id: UUID | None = None

    async def get_me(self, *, user_id: UUID):
        raise AssertionError("delete_me route must not call get_me")

    async def delete_me(self, *, user_id: UUID) -> None:
        self.received_delete_user_id = user_id


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
