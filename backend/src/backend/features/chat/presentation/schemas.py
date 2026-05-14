from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ChatUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=120)


class ChatResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    system_prompt: str | None
    created_at: datetime
    updated_at: datetime


class ErrorResponse(BaseModel):
    detail: str
