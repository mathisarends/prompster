from datetime import datetime
from uuid import UUID

from backend.features.user.domain.spotify_account import SpotifyAccount
from backend.shared.ddd import Aggregate


class User(Aggregate):
    def __init__(
        self,
        *,
        name: str,
        email: str,
        profile_image_url: str | None = None,
        spotify: SpotifyAccount | None = None,
        id: UUID | None = None,
        created_time: datetime | None = None,
    ) -> None:
        super().__init__(id=id, created_time=created_time)
        self.name = name
        self.email = email
        self.profile_image_url = profile_image_url
        self.spotify = spotify or SpotifyAccount.disconnected()
