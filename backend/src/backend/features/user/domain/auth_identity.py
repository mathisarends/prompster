from datetime import UTC, datetime
from enum import StrEnum
from typing import Self
from uuid import UUID, uuid4

from backend.shared.ddd import Entity


class AuthProvider(StrEnum):
    GOOGLE = "google"
    SPOTIFY = "spotify"


class AuthIdentity(Entity):
    def __init__(
        self,
        *,
        id: UUID,
        created_at: datetime,
        user_id: UUID,
        provider: AuthProvider,
        subject: str,
    ) -> None:
        super().__init__(id=id, created_at=created_at)
        self.user_id = user_id
        self.provider = provider
        self.subject = subject

    @classmethod
    def create(
        cls,
        *,
        user_id: UUID,
        provider: AuthProvider,
        subject: str,
    ) -> Self:
        return cls(
            id=uuid4(),
            created_at=datetime.now(UTC),
            user_id=user_id,
            provider=provider,
            subject=subject,
        )

    @classmethod
    def restore(
        cls,
        *,
        id: UUID,
        created_at: datetime,
        user_id: UUID,
        provider: AuthProvider,
        subject: str,
    ) -> Self:
        return cls(
            id=id,
            created_at=created_at,
            user_id=user_id,
            provider=provider,
            subject=subject,
        )
