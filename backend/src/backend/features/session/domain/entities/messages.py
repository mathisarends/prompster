from datetime import datetime
from enum import StrEnum
from uuid import UUID

from backend.shared.ddd import Entity


class UserMessageAttachmentKind(StrEnum):
    SPOTIFY_PLAYLIST = "spotify-playlist"
    SPOTIFY_ARTIST = "spotify-artist"


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


class UserMessage(Entity):
    def __init__(
        self,
        content: str,
        attachments: list[UserMessageAttachment] | None = None,
        id: UUID | None = None,
        created_time: datetime | None = None,
    ) -> None:
        super().__init__(id=id, created_time=created_time)
        self.content = content
        self.attachments = tuple(attachments or [])


class AssistantMessage(Entity):
    def __init__(
        self,
        content: str = "",
        id: UUID | None = None,
        created_time: datetime | None = None,
    ) -> None:
        super().__init__(id=id, created_time=created_time)
        self.content = content
