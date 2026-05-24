from datetime import datetime
from enum import StrEnum
from uuid import UUID

from backend.shared.ddd import Entity


class AuthProvider(StrEnum):
    GOOGLE = "google"
    SPOTIFY = "spotify"


class AuthIdentity(Entity):
    def __init__(
        self,
        *,
        user_id: UUID,
        provider: AuthProvider,
        subject: str,
        id: UUID | None = None,
        created_time: datetime | None = None,
    ) -> None:
        super().__init__(id=id, created_time=created_time)
        self.user_id = user_id
        self.provider = provider
        self.subject = subject
