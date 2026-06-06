from datetime import datetime
from enum import StrEnum
from uuid import UUID

from backend.shared.ddd import Entity


class UserMessageAttachmentKind(StrEnum):
    SPOTIFY_PLAYLIST = "spotify-playlist"
    SPOTIFY_ARTIST = "spotify-artist"


class UserCurationEventType(StrEnum):
    TRACK_ADDED = "track_added"
    TRACK_REMOVED = "track_removed"


class UserCurationEvent(Entity):
    def __init__(
        self,
        event_type: UserCurationEventType,
        track_id: UUID,
        track_title: str,
        track_artist: str,
        track_year: int | None = None,
        track_spotify_uri: str | None = None,
        track_cover_url: str | None = None,
        consumed: bool = False,
        id: UUID | None = None,
        created_time: datetime | None = None,
    ) -> None:
        super().__init__(id=id, created_time=created_time)
        if track_year is not None and not 1900 <= track_year <= 2100:
            raise ValueError("track_year must be between 1900 and 2100.")

        self.event_type = event_type
        self.track_id = track_id
        self.track_title = track_title
        self.track_artist = track_artist
        self.track_year = track_year
        self.track_spotify_uri = track_spotify_uri
        self.track_cover_url = track_cover_url
        self.consumed = consumed

    @property
    def occurred_at(self) -> datetime:
        return self.created_at

    def mark_consumed(self) -> None:
        self.consumed = True


class UserMessageAttachment:
    def __init__(
        self,
        *,
        kind: UserMessageAttachmentKind,
        external_id: str,
        title: str,
        subtitle: str | None = None,
        image_url: str | None = None,
        spotify_id: str | None = None,
    ) -> None:
        self.kind = kind
        self.external_id = external_id
        self.title = title
        self.subtitle = subtitle
        self.image_url = image_url
        self.spotify_id = spotify_id


class ImageAttachment(Entity):
    def __init__(
        self,
        *,
        storage_key: str,
        content_type: str,
        file_name: str,
        size_bytes: int,
        id: UUID | None = None,
        created_time: datetime | None = None,
    ) -> None:
        super().__init__(id=id, created_time=created_time)
        self.storage_key = storage_key
        self.content_type = content_type
        self.file_name = file_name
        self.size_bytes = size_bytes


class UserMessage(Entity):
    def __init__(
        self,
        content: str,
        attachments: list[UserMessageAttachment] | None = None,
        image_attachments: list[ImageAttachment] | None = None,
        user_curation_events: list[UserCurationEvent] | None = None,
        id: UUID | None = None,
        created_time: datetime | None = None,
    ) -> None:
        super().__init__(id=id, created_time=created_time)
        self.content = content
        self.attachments = tuple(attachments or [])
        self.image_attachments = tuple(image_attachments or [])
        self.user_curation_events = tuple(user_curation_events or [])


class AssistantMessage(Entity):
    def __init__(
        self,
        content: str = "",
        id: UUID | None = None,
        created_time: datetime | None = None,
    ) -> None:
        super().__init__(id=id, created_time=created_time)
        self.content = content
