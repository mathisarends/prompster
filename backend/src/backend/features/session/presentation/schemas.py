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


class SessionMessageAttachmentKind(StrEnum):
    SPOTIFY_PLAYLIST = "spotify-playlist"
    SPOTIFY_ARTIST = "spotify-artist"


class SessionMessageAttachmentRequest(Schema):
    kind: SessionMessageAttachmentKind
    external_id: str = Field(min_length=1, max_length=128)
    title: str = Field(min_length=1, max_length=300)
    subtitle: str | None = Field(default=None, max_length=300)
    image_url: str | None = Field(default=None, max_length=2048)
    spotify_id: str | None = Field(default=None, min_length=1, max_length=128)


class SessionMessageAttachmentResponse(Schema):
    kind: SessionMessageAttachmentKind
    external_id: str
    title: str
    subtitle: str | None = None
    image_url: str | None = None
    spotify_id: str | None = None


class UserMessageEntryResponse(Schema):
    kind: Literal[EntryKind.USER_MESSAGE] = EntryKind.USER_MESSAGE
    id: UUID
    content: str
    attachments: list[SessionMessageAttachmentResponse] = Field(default_factory=list)
    created_at: datetime


class AssistantMessageEntryResponse(Schema):
    kind: Literal[EntryKind.ASSISTANT_MESSAGE] = EntryKind.ASSISTANT_MESSAGE
    id: UUID
    content: str
    created_at: datetime


class ToolCallState(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class ToolFunctionResponse(Schema):
    name: str
    arguments: dict[str, object]
    status_label: str | None = None
    action_type: str | None = None


class ToolCallResponse(Schema):
    id: str
    function: ToolFunctionResponse
    state: ToolCallState
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


class PlaylistTrackResponse(Schema):
    id: UUID
    title: str
    artist: str
    year: int | None = None
    spotify_uri: str | None = None
    cover_url: str | None = None
    is_pinned: bool


class PlaylistResponse(Schema):
    id: UUID
    name: str | None = None
    tracks: list[PlaylistTrackResponse]


class UserCurationEventTypeResponse(StrEnum):
    TRACK_PINNED = "track_pinned"
    TRACK_UNPINNED = "track_unpinned"
    TRACK_ADDED = "track_added"
    TRACK_REMOVED = "track_removed"


class UserCurationEventResponse(Schema):
    id: UUID
    event_type: UserCurationEventTypeResponse
    track_id: UUID
    track_title: str
    track_artist: str
    track_spotify_uri: str | None = None
    track_cover_url: str | None = None
    history_index: int | None = Field(default=None, ge=0)
    occurred_at: datetime


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
    playlist: PlaylistResponse | None = None
    unconsumed_user_curation_events: list[UserCurationEventResponse] = Field(
        default_factory=list
    )


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
    attachments: list[SessionMessageAttachmentRequest] = Field(
        default_factory=list,
        max_length=25,
    )

    @model_validator(mode="after")
    def validate_unique_attachments(self) -> Self:
        seen: set[tuple[str, str]] = set()
        for attachment in self.attachments:
            key = (attachment.kind.value, attachment.external_id)
            if key in seen:
                raise ValueError("Duplicate attachments are not allowed.")
            seen.add(key)
        return self


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
    spotify_uri: str | None = None
    cover_url: str | None = None
    is_pinned: bool = True


class SpotifyPlaylistExportResponse(Schema):
    id: str
    name: str
    description: str
    url: str
    track_count: int


class ErrorResponse(Schema):
    detail: str
