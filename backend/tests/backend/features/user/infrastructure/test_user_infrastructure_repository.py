import asyncio
from unittest.mock import AsyncMock, Mock

from backend.features.user.domain import AuthIdentity, AuthProvider, User
from backend.features.user.infrastructure.repository import SqlUserRepository
from backend.infrastructure.database.orm import AuthIdentityModel, UserModel


def test_create_with_auth_identity_flushes_user_before_identity_insert() -> None:
    session = Mock()
    session.add = Mock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()

    repository = SqlUserRepository(session=session)  # type: ignore[arg-type]
    user = User(
        name="Mathis",
        email="mathis@example.com",
        profile_image_url="https://example.com/avatar.jpg",
    )
    auth_identity = AuthIdentity(
        user_id=user.id,
        provider=AuthProvider.GOOGLE,
        subject="google-subject-1",
    )

    created_user = asyncio.run(
        repository.create_with_auth_identity(user=user, auth_identity=auth_identity)
    )

    assert isinstance(session.add.call_args_list[0].args[0], UserModel)
    assert isinstance(session.add.call_args_list[1].args[0], AuthIdentityModel)
    assert session.mock_calls[0][0] == "add"
    assert session.mock_calls[1][0] == "flush"
    assert session.mock_calls[2][0] == "add"
    assert session.mock_calls[3][0] == "flush"
    assert session.mock_calls[4][0] == "refresh"
    assert session.flush.await_count == 2
    assert created_user.id == user.id
    created_user_model = session.add.call_args_list[0].args[0]
    assert created_user_model.profile_image_url == "https://example.com/avatar.jpg"
