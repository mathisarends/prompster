from datetime import UTC, datetime
from enum import StrEnum
from typing import Self
from uuid import UUID, uuid4

from backend.shared.ddd import Aggregate


class OAuthProvider(StrEnum):
    SPOTIFY = "spotify"


class OAuthConnection(Aggregate):
    def __init__(
        self,
        *,
        id: UUID,
        created_at: datetime,
        user_id: UUID,
        provider: OAuthProvider,
        provider_user_id: str,
        refresh_token: str,
        scope: str,
        connected_at: datetime,
        is_premium: bool = False,
    ) -> None:
        super().__init__(id=id, created_time=created_at)
        self.user_id = user_id
        self.provider = provider
        self.provider_user_id = provider_user_id
        self.refresh_token = refresh_token
        self.scope = scope
        self.connected_at = connected_at
        self.is_premium = is_premium

    @classmethod
    def create(
        cls,
        *,
        user_id: UUID,
        provider: OAuthProvider,
        provider_user_id: str,
        refresh_token: str,
        scope: str,
        connected_at: datetime,
        is_premium: bool = False,
    ) -> Self:
        return cls(
            id=uuid4(),
            created_at=datetime.now(UTC),
            user_id=user_id,
            provider=provider,
            provider_user_id=provider_user_id,
            refresh_token=refresh_token,
            scope=scope,
            connected_at=connected_at,
            is_premium=is_premium,
        )

    @classmethod
    def restore(
        cls,
        *,
        id: UUID,
        created_at: datetime,
        user_id: UUID,
        provider: OAuthProvider,
        provider_user_id: str,
        refresh_token: str,
        scope: str,
        connected_at: datetime,
        is_premium: bool = False,
    ) -> Self:
        return cls(
            id=id,
            created_at=created_at,
            user_id=user_id,
            provider=provider,
            provider_user_id=provider_user_id,
            refresh_token=refresh_token,
            scope=scope,
            connected_at=connected_at,
            is_premium=is_premium,
        )

    def rotate_refresh_token(self, *, new_refresh_token: str) -> None:
        self.refresh_token = new_refresh_token

    def update_premium_status(self, *, is_premium: bool) -> None:
        self.is_premium = is_premium
