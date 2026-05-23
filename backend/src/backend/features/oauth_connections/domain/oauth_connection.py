from datetime import datetime
from enum import StrEnum
from uuid import UUID

from backend.shared.ddd import Aggregate


class OAuthProvider(StrEnum):
    SPOTIFY = "spotify"


class OAuthConnection(Aggregate):
    def __init__(
        self,
        *,
        user_id: UUID,
        provider: OAuthProvider,
        provider_user_id: str,
        encrypted_refresh_token: bytes,
        scope: str,
        connected_at: datetime,
        is_premium: bool = False,
        id: UUID | None = None,
        created_time: datetime | None = None,
    ) -> None:
        super().__init__(id=id, created_time=created_time)
        self.user_id = user_id
        self.provider = provider
        self.provider_user_id = provider_user_id
        self.encrypted_refresh_token = encrypted_refresh_token
        self.scope = scope
        self.connected_at = connected_at
        self.is_premium = is_premium

    def rotate_refresh_token(self, *, new_encrypted_refresh_token: bytes) -> None:
        self.encrypted_refresh_token = new_encrypted_refresh_token

    def update_premium_status(self, *, is_premium: bool) -> None:
        self.is_premium = is_premium
