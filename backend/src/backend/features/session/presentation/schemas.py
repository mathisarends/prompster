from datetime import datetime
from enum import StrEnum
from typing import Self
from uuid import UUID

from pydantic import Field, model_validator

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


class FollowUpAction(StrEnum):
    ANSWER = "answer"
    SKIP_REMAINING = "skip_remaining"


class FollowUpAnswerRequest(Schema):
    question_id: UUID
    option_id: str | None = Field(default=None, min_length=1, max_length=120)
    text: str | None = Field(default=None, min_length=1, max_length=4000)

    @model_validator(mode="after")
    def require_exactly_one_answer(self) -> Self:
        has_option = self.option_id is not None
        has_text = self.text is not None
        if has_option == has_text:
            raise ValueError("Provide exactly one of option_id or text.")
        return self


class FollowUpRequest(Schema):
    action: FollowUpAction
    answers: list[FollowUpAnswerRequest] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_action_fields(self) -> Self:
        if self.action == FollowUpAction.ANSWER:
            if not self.answers:
                raise ValueError(
                    "Provide at least one answer for a follow-up answer action."
                )
            return self

        if self.answers:
            raise ValueError("Do not provide answers for a follow-up skip action.")
        return self


class AddPlaylistTrackRequest(Schema):
    title: str = Field(min_length=1, max_length=300)
    artist: str = Field(min_length=1, max_length=300)
    year: int | None = Field(default=None, ge=1900, le=2100)
    cover_url: str | None = None


class PlaylistTrackResponse(Schema):
    id: UUID
    title: str
    artist: str
    year: int | None = None
    cover_url: str | None = None


class ErrorResponse(Schema):
    detail: str
