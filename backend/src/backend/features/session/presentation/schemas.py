from datetime import datetime
from uuid import UUID

from pydantic import Field

from backend.features.session.domain import MessageRole
from backend.presentation.schema import Schema


class SessionCreateRequest(Schema):
    initial_prompt: str = Field(min_length=1, max_length=4000)


class SessionUpdateRequest(Schema):
    title: str = Field(min_length=1, max_length=120)


class MessageResponse(Schema):
    id: UUID
    role: MessageRole
    content: str
    created_at: datetime


class SessionResponse(Schema):
    id: UUID
    title: str
    created_at: datetime
    messages: list[MessageResponse]


class SessionSummaryResponse(Schema):
    id: UUID
    title: str
    created_at: datetime
    last_activity_at: datetime


class SessionSummaryListResponse(Schema):
    items: list[SessionSummaryResponse]


class SendMessageRequest(Schema):
    content: str = Field(min_length=1, max_length=4000)


class SpotifyTrackResponse(Schema):
    id: str
    title: str
    artist: str
    album: str | None = None
    year: int | None = None
    cover_url: str | None = None
    preview_url: str | None = None


class SpotifyTrackSearchResponse(Schema):
    items: list[SpotifyTrackResponse]


class ErrorResponse(Schema):
    detail: str
