from datetime import datetime
from enum import StrEnum
from uuid import UUID

from backend.shared.ddd import Entity


class WorkspaceEventType(StrEnum):
    TRACK_PINNED = "track_pinned"
    TRACK_UNPINNED = "track_unpinned"
    TRACK_ADDED = "track_added"
    TRACK_REMOVED = "track_removed"


class WorkspaceEvent(Entity):
    def __init__(
        self,
        event_type: WorkspaceEventType,
        track_id: UUID,
        track_title: str,
        track_artist: str,
        track_spotify_uri: str | None = None,
        track_cover_url: str | None = None,
        consumed: bool = False,
        id: UUID | None = None,
        created_time: datetime | None = None,
    ) -> None:
        super().__init__(id=id, created_time=created_time)
        self.event_type = event_type
        self.track_id = track_id
        self.track_title = track_title
        self.track_artist = track_artist
        self.track_spotify_uri = track_spotify_uri
        self.track_cover_url = track_cover_url
        self.consumed = consumed

    @property
    def occurred_at(self) -> datetime:
        return self.created_at

    def mark_consumed(self) -> None:
        self.consumed = True
