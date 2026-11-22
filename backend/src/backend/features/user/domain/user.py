from datetime import UTC, datetime
from typing import Self
from uuid import UUID, uuid4

from backend.features.user.domain.spotify_account import SpotifyAccount
from backend.shared.ddd import Aggregate


class User(Aggregate):
    def __init__(
        self,
        *,
        id: UUID,
        created_at: datetime,
        name: str,
        profile_image_url: str | None = None,
        spotify: SpotifyAccount | None = None,
    ) -> None:
        super().__init__(id=id, created_at=created_at)
        self.name = name
        self.profile_image_url = profile_image_url
        self.spotify = spotify if spotify is not None else SpotifyAccount.disconnected()

    @classmethod
    def create(
        cls,
        *,
        name: str,
        profile_image_url: str | None = None,
        spotify: SpotifyAccount | None = None,
    ) -> Self:
        return cls(
            id=uuid4(),
            created_at=datetime.now(UTC),
            name=name,
            profile_image_url=profile_image_url,
            spotify=spotify,
        )

    @classmethod
    def restore(
        cls,
        *,
        id: UUID,
        created_at: datetime,
        name: str,
        profile_image_url: str | None = None,
        spotify: SpotifyAccount | None = None,
    ) -> Self:
        return cls(
            id=id,
            created_at=created_at,
            name=name,
            profile_image_url=profile_image_url,
            spotify=spotify,
        )
