from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SessionCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    system_prompt: str | None = Field(default=None, max_length=4000)


class SessionUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=120)
    system_prompt: str | None = Field(default=None, max_length=4000)


class SessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    system_prompt: str | None
    created_at: datetime


class ErrorResponse(BaseModel):
    detail: str
