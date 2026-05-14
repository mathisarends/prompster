from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ChatCreateRequestSchema(BaseModel):
	title: str = Field(min_length=1, max_length=120)
	system_prompt: str | None = Field(default=None, max_length=4000)


class ChatUpdateRequestSchema(BaseModel):
	title: str | None = Field(default=None, min_length=1, max_length=120)
	system_prompt: str | None = Field(default=None, max_length=4000)


class ChatResponseSchema(BaseModel):
	id: UUID
	title: str
	system_prompt: str | None
	created_at: datetime
	updated_at: datetime

