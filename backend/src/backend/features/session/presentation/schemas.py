from datetime import datetime
from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from backend.features.session.domain.views import MessageRole


class SessionCreateRequest(BaseModel):
    initial_prompt: str = Field(min_length=1, max_length=4000)
    system_prompt: str | None = Field(default=None, max_length=4000)


class SessionUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=120)
    system_prompt: str | None = Field(default=None, max_length=4000)

    @model_validator(mode="after")
    def validate_at_least_one_field(self) -> Self:
        if self.title is None and self.system_prompt is None:
            raise ValueError("At least one field must be provided for update")
        return self


class SessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    system_prompt: str | None
    created_at: datetime


class SendMessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=4000)


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    role: MessageRole
    content: str
    created_at: datetime


class ErrorResponse(BaseModel):
    detail: str
