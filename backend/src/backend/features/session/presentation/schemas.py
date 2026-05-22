from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal, Self, Union
from uuid import UUID

from pydantic import Field, model_validator

from backend.presentation.schema import Schema


class SessionCreateRequest(Schema):
    initial_prompt: str = Field(min_length=1, max_length=4000)


class SessionUpdateRequest(Schema):
    title: str = Field(min_length=1, max_length=120)


class EntryKind(StrEnum):
    USER_MESSAGE = "user_message"
    ASSISTANT_MESSAGE = "assistant_message"
    TOOL_CALL_SEQUENCE = "tool_call_sequence"
    FOLLOW_UP_QUESTION_GROUP = "follow_up_question_group"


class UserMessageEntryResponse(Schema):
    kind: Literal[EntryKind.USER_MESSAGE] = EntryKind.USER_MESSAGE
    id: UUID
    content: str
    created_at: datetime


class AssistantMessageEntryResponse(Schema):
    kind: Literal[EntryKind.ASSISTANT_MESSAGE] = EntryKind.ASSISTANT_MESSAGE
    id: UUID
    content: str
    created_at: datetime


class ToolFunctionResponse(Schema):
    name: str
    arguments: dict[str, object]
    status_label: str | None = None


class ToolCallResponse(Schema):
    id: str
    function: ToolFunctionResponse
    state: Literal["pending", "completed", "failed"]
    result: str | None = None
    error: str | None = None


class ToolCallSequenceEntryResponse(Schema):
    kind: Literal[EntryKind.TOOL_CALL_SEQUENCE] = EntryKind.TOOL_CALL_SEQUENCE
    id: UUID
    created_at: datetime
    calls: list[ToolCallResponse]


class FollowUpOptionResponse(Schema):
    id: str
    label: str


class FollowUpQuestionResponse(Schema):
    id: UUID
    question: str
    options: list[FollowUpOptionResponse]
    state: Literal["pending", "answered", "skipped"]
    answer_text: str | None = None
    answered_option_id: str | None = None


class FollowUpQuestionGroupEntryResponse(Schema):
    kind: Literal[EntryKind.FOLLOW_UP_QUESTION_GROUP] = (
        EntryKind.FOLLOW_UP_QUESTION_GROUP
    )
    id: UUID
    created_at: datetime
    questions: list[FollowUpQuestionResponse]


SessionEntryResponse = Annotated[
    Union[
        UserMessageEntryResponse,
        AssistantMessageEntryResponse,
        ToolCallSequenceEntryResponse,
        FollowUpQuestionGroupEntryResponse,
    ],
    Field(discriminator="kind"),
]


class SessionResponse(Schema):
    id: UUID
    title: str
    is_starred: bool
    created_at: datetime
    entries: list[SessionEntryResponse]


class SessionSummaryResponse(Schema):
    id: UUID
    title: str
    is_starred: bool
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
