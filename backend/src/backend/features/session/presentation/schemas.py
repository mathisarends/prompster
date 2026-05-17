from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from backend.features.session.domain import MessageRole


class SessionCreateRequest(BaseModel):
    initial_prompt: str = Field(min_length=1, max_length=4000)


class SessionUpdateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=120)


class SessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    created_at: datetime


class SendMessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=4000)


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    role: MessageRole
    content: str
    created_at: datetime


class SpotifyTrackResponse(BaseModel):
    id: str
    title: str
    artist: str
    album: str | None = None
    year: int | None = None
    cover_url: str | None = None
    preview_url: str | None = None


class SpotifyTrackSearchResponse(BaseModel):
    items: list[SpotifyTrackResponse]


class ErrorResponse(BaseModel):
    detail: str
