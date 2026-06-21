from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal, Self, Union
from uuid import UUID

from pydantic import Field, RootModel, model_validator

from backend.features.session.domain import OnboardingQuestionSelectionMode, Phase
from backend.presentation.schema import Schema


class SessionCreateRequest(Schema):
    initial_prompt: str = Field(min_length=1, max_length=4000)


class SessionUpdateRequest(Schema):
    title: str = Field(min_length=1, max_length=120)


class EntryKind(StrEnum):
    USER_MESSAGE = "user_message"
    ASSISTANT_MESSAGE = "assistant_message"
    TOOL_CALL_SEQUENCE = "tool_call_sequence"


class EntryKindSchema(RootModel[EntryKind]):
    """Schema-only model to expose EntryKind in OpenAPI."""


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


class ImageAttachmentResponse(Schema):
    id: UUID
    url: str | None = None
    content_type: str
    file_name: str
    size_bytes: int


class UploadedImageAttachmentResponse(ImageAttachmentResponse):
    storage_key: str


class ImageAttachmentReferenceRequest(Schema):
    id: UUID
    storage_key: str = Field(min_length=1, max_length=1024)
    content_type: str = Field(min_length=1, max_length=128)
    file_name: str = Field(min_length=1, max_length=300)
    size_bytes: int = Field(gt=0)


class UserMessageEntryResponse(Schema):
    kind: Literal[EntryKind.USER_MESSAGE] = EntryKind.USER_MESSAGE
    id: UUID
    content: str
    attachments: list[SessionMessageAttachmentResponse] = Field(default_factory=list)
    image_attachments: list[str] = Field(default_factory=list)
    user_curation_events: list["UserCurationEventResponse"] = Field(
        default_factory=list
    )
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


class PlaylistTrackResponse(Schema):
    id: UUID
    title: str
    artist: str
    year: int
    spotify_uri: str | None = None
    cover_url: str | None = None


class PlaylistResponse(Schema):
    id: UUID
    name: str | None = None
    tracks: list[PlaylistTrackResponse]


class UserCurationEventTypeResponse(StrEnum):
    TRACK_ADDED = "track_added"
    TRACK_REMOVED = "track_removed"


class UserCurationEventResponse(Schema):
    id: UUID
    event_type: UserCurationEventTypeResponse
    track_id: UUID
    track_title: str
    track_artist: str
    track_year: int | None = Field(default=None, ge=1900, le=2100)
    track_spotify_uri: str | None = None
    track_cover_url: str | None = None
    occurred_at: datetime


class PlaylistReferenceResponse(Schema):
    id: UUID
    spotify_playlist_id: str
    name: str
    owner: str | None = None
    cover_url: str | None = None
    total_tracks: int | None = None


class ArtistReferenceResponse(Schema):
    id: UUID
    spotify_artist_id: str
    name: str
    image_url: str | None = None
    genres: list[str] = Field(default_factory=list)
    followers: int | None = None
    popularity: int | None = None


class OnboardingQuestionResponse(Schema):
    id: UUID
    sequence_number: int
    question_text: str
    hint: str | None = None
    options: list[str] = Field(default_factory=list)
    recommended_option: str | None = None
    selection_mode: OnboardingQuestionSelectionMode = (
        OnboardingQuestionSelectionMode.SINGLE_SELECT
    )
    is_last_question: bool
    answers: list[str] = Field(default_factory=list)
    is_answered: bool = False


UserMessageEntryResponse.model_rebuild()


SessionEntryResponse = Annotated[
    Union[
        UserMessageEntryResponse,
        AssistantMessageEntryResponse,
        ToolCallSequenceEntryResponse,
    ],
    Field(discriminator="kind"),
]


class SessionResponse(Schema):
    id: UUID
    title: str
    is_starred: bool
    phase: Phase
    created_at: datetime
    entries: list[SessionEntryResponse]
    playlist: PlaylistResponse | None = None
    playlist_references: list[PlaylistReferenceResponse] = Field(default_factory=list)
    artist_references: list[ArtistReferenceResponse] = Field(default_factory=list)
    unconsumed_user_curation_events: list[UserCurationEventResponse] = Field(
        default_factory=list
    )
    onboarding_questions: list[OnboardingQuestionResponse] = Field(default_factory=list)


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
    image_attachments: list[ImageAttachmentReferenceRequest] = Field(
        default_factory=list,
        max_length=5,
    )

    @model_validator(mode="after")
    def validate_unique_attachments(self) -> Self:
        seen: set[tuple[str, str]] = set()
        for attachment in self.attachments:
            key = (attachment.kind.value, attachment.external_id)
            if key in seen:
                raise ValueError("Duplicate attachments are not allowed.")
            seen.add(key)
        image_ids: set[UUID] = set()
        image_storage_keys: set[str] = set()
        for attachment in self.image_attachments:
            if (
                attachment.id in image_ids
                or attachment.storage_key in image_storage_keys
            ):
                raise ValueError("Duplicate image attachments are not allowed.")
            image_ids.add(attachment.id)
            image_storage_keys.add(attachment.storage_key)
        return self


class SubmitOnboardingAnswerRequest(Schema):
    question_id: UUID
    answer: str | None = Field(default=None, min_length=1, max_length=2000)
    answers: list[str] = Field(default_factory=list, max_length=8)

    @model_validator(mode="after")
    def validate_answer_payload(self) -> Self:
        if self.answer is not None and self.answer.strip():
            return self
        if any(answer.strip() for answer in self.answers):
            return self
        raise ValueError("At least one onboarding answer is required.")


class AddPlaylistTrackRequest(Schema):
    title: str = Field(min_length=1, max_length=300)
    artist: str = Field(min_length=1, max_length=300)
    year: int = Field(ge=1900, le=2100)
    spotify_uri: str | None = None
    cover_url: str | None = None


class SpotifyPlaylistExportResponse(Schema):
    id: str
    name: str
    description: str
    url: str
    track_count: int


class ErrorResponse(Schema):
    detail: str
