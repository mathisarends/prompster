from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel


class UserCurationEventType(StrEnum):
    TRACK_ADDED = "track_added"
    TRACK_REMOVED = "track_removed"


class UserEvent(BaseModel):
    """A manual playlist change the user made outside of the agent's tools.

    Bound to a single user turn — events represent what the user changed
    between the previous turn and the moment they sent their next message.
    """

    type: UserCurationEventType
    occurred_at: datetime
    track_title: str | None = None
    track_artist: str | None = None

    @property
    def label(self) -> str:
        if self.track_artist and self.track_title:
            return f"{self.track_artist} - {self.track_title}"
        if self.track_artist:
            return self.track_artist
        if self.track_title:
            return self.track_title
        return self.type.replace("_", " ")


type UserEvents = list[UserEvent]
