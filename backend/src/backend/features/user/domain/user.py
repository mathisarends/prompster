from datetime import datetime
from uuid import UUID

from backend.shared.ddd import Aggregate


class User(Aggregate):
    def __init__(
        self,
        *,
        name: str,
        email: str,
        google_subject: str,
        spotify_connected: bool = False,
        id: UUID | None = None,
        created_time: datetime | None = None,
    ) -> None:
        super().__init__(id=id, created_time=created_time)
        self.name = name
        self.email = email
        self.google_subject = google_subject
        self.spotify_connected = spotify_connected
