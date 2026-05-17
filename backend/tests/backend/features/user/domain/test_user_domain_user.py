from datetime import datetime, timezone
from uuid import UUID, uuid4

from backend.features.user.domain.user import User


class TestUserDomainUser:
    def test_user_assigns_constructor_fields(self) -> None:
        user = User(
            name="Mathis",
            email="mathis@example.com",
            google_subject="google-subject-1",
        )

        assert user.name == "Mathis"
        assert user.email == "mathis@example.com"
        assert user.google_subject == "google-subject-1"

    def test_user_keeps_explicit_id_and_created_time(self) -> None:
        user_id: UUID = uuid4()
        created_time = datetime(2025, 1, 1, tzinfo=timezone.utc)

        user = User(
            name="Mathis",
            email="mathis@example.com",
            google_subject="google-subject-1",
            id=user_id,
            created_time=created_time,
        )

        assert user.id == user_id
        assert user.created_at == created_time
