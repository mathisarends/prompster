from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class UserCurationEventType(StrEnum):
    TRACK_PINNED = "track_pinned"
    TRACK_UNPINNED = "track_unpinned"
    TRACK_ADDED = "track_added"
    TRACK_REMOVED = "track_removed"


class UserEvent(BaseModel):
    type: UserCurationEventType
    occurred_at: datetime
    track_title: str | None = None
    track_artist: str | None = None
    history_index: int | None = Field(default=None, ge=0)

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
