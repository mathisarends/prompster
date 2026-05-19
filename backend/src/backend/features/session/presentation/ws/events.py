from datetime import datetime
from typing import Annotated, Literal, Union
from uuid import UUID

from pydantic import Field

from backend.features.session.domain import (
    FollowUpQuestionState,
    MessageRole,
    ToolCallState,
)
from backend.presentation.schema import Schema


class _WsEvent(Schema):
    pass


class FollowUpOptionPayload(_WsEvent):
    id: str
    label: str


class FollowUpQuestionPayload(_WsEvent):
    id: UUID
    question: str
    options: list[FollowUpOptionPayload]
    state: FollowUpQuestionState
    answer_text: str | None = None
    answered_option_id: str | None = None


class FollowUpQuestionGroupPayload(_WsEvent):
    id: UUID
    questions: list[FollowUpQuestionPayload]


class ToolFunctionPayload(_WsEvent):
    name: str
    arguments: dict[str, object]


class ToolCallPayload(_WsEvent):
    id: str
    function: ToolFunctionPayload
    state: ToolCallState
    result: str | None = None
    error: str | None = None


class ToolCallGroupPayload(_WsEvent):
    id: UUID
    calls: list[ToolCallPayload]


class PlaylistTrackPayload(_WsEvent):
    id: UUID
    title: str
    artist: str
    year: int | None = None
    cover_url: str | None = None


class PlaylistPayload(_WsEvent):
    id: UUID
    name: str | None = None
    tracks: list[PlaylistTrackPayload]


class MessagePayload(_WsEvent):
    id: UUID
    role: MessageRole
    content: str
    created_at: datetime
    tool_call_group: ToolCallGroupPayload | None = None
    follow_up_group: FollowUpQuestionGroupPayload | None = None


class SessionSnapshotPayload(_WsEvent):
    id: UUID
    title: str
    created_at: datetime
    messages: list[MessagePayload]
    playlist: PlaylistPayload | None = None


class SessionSnapshotEvent(_WsEvent):
    type: Literal["session.snapshot"] = "session.snapshot"
    session: SessionSnapshotPayload


class SessionTitleGeneratedEvent(_WsEvent):
    type: Literal["session.title_generated"] = "session.title_generated"
    session_id: UUID
    title: str


class UserMessageAppendedEvent(_WsEvent):
    type: Literal["message.user_appended"] = "message.user_appended"
    message: MessagePayload


class AssistantMessageStartedEvent(_WsEvent):
    type: Literal["message.assistant_started"] = "message.assistant_started"
    message_id: UUID
    created_at: datetime


class AssistantMessageChunkEvent(_WsEvent):
    type: Literal["message.assistant_chunk"] = "message.assistant_chunk"
    message_id: UUID
    chunk: str


class AssistantMessageCompletedEvent(_WsEvent):
    type: Literal["message.assistant_completed"] = "message.assistant_completed"
    message: MessagePayload


class AssistantMessageCancelledEvent(_WsEvent):
    type: Literal["message.assistant_cancelled"] = "message.assistant_cancelled"
    message_id: UUID


class ToolCallGroupAddedEvent(_WsEvent):
    type: Literal["tool_call.group_added"] = "tool_call.group_added"
    message_id: UUID
    group: ToolCallGroupPayload


class ToolCallResolvedEvent(_WsEvent):
    type: Literal["tool_call.resolved"] = "tool_call.resolved"
    group_id: UUID
    tool_call_id: str
    result: str


class ToolCallFailedEvent(_WsEvent):
    type: Literal["tool_call.failed"] = "tool_call.failed"
    group_id: UUID
    tool_call_id: str
    error: str


class ToolCallGroupCompletedEvent(_WsEvent):
    type: Literal["tool_call.group_completed"] = "tool_call.group_completed"
    group_id: UUID


class FollowUpGroupAddedEvent(_WsEvent):
    type: Literal["follow_up.group_added"] = "follow_up.group_added"
    message_id: UUID
    group: FollowUpQuestionGroupPayload


class FollowUpAnsweredEvent(_WsEvent):
    type: Literal["follow_up.answered"] = "follow_up.answered"
    group_id: UUID
    question_id: UUID
    answer_text: str
    answered_option_id: str | None = None


class FollowUpSkippedEvent(_WsEvent):
    type: Literal["follow_up.skipped"] = "follow_up.skipped"
    group_id: UUID
    question_id: UUID


class FollowUpGroupCompletedEvent(_WsEvent):
    type: Literal["follow_up.group_completed"] = "follow_up.group_completed"
    group_id: UUID


class PlaylistSetEvent(_WsEvent):
    type: Literal["playlist.set"] = "playlist.set"
    playlist: PlaylistPayload


class PlaylistTrackAddedEvent(_WsEvent):
    type: Literal["playlist.track_added"] = "playlist.track_added"
    playlist_id: UUID
    track: PlaylistTrackPayload


class PlaylistTrackRemovedEvent(_WsEvent):
    type: Literal["playlist.track_removed"] = "playlist.track_removed"
    playlist_id: UUID
    track_id: UUID


class ErrorEvent(_WsEvent):
    type: Literal["error"] = "error"
    code: str
    message: str
    correlation_id: str | None = None


ServerEvent = Annotated[
    Union[
        SessionSnapshotEvent,
        SessionTitleGeneratedEvent,
        UserMessageAppendedEvent,
        AssistantMessageStartedEvent,
        AssistantMessageChunkEvent,
        AssistantMessageCompletedEvent,
        AssistantMessageCancelledEvent,
        ToolCallGroupAddedEvent,
        ToolCallResolvedEvent,
        ToolCallFailedEvent,
        ToolCallGroupCompletedEvent,
        FollowUpGroupAddedEvent,
        FollowUpAnsweredEvent,
        FollowUpSkippedEvent,
        FollowUpGroupCompletedEvent,
        PlaylistSetEvent,
        PlaylistTrackAddedEvent,
        PlaylistTrackRemovedEvent,
        ErrorEvent,
    ],
    Field(discriminator="type"),
]


class SendMessageCommand(_WsEvent):
    type: Literal["message.send"] = "message.send"
    content: str = Field(min_length=1, max_length=4000)
    correlation_id: str | None = None


class AnswerFollowUpWithOptionCommand(_WsEvent):
    type: Literal["follow_up.answer_option"] = "follow_up.answer_option"
    question_id: UUID
    option_id: str = Field(min_length=1, max_length=120)
    correlation_id: str | None = None


class AnswerFollowUpWithTextCommand(_WsEvent):
    type: Literal["follow_up.answer_text"] = "follow_up.answer_text"
    question_id: UUID
    text: str = Field(min_length=1, max_length=4000)
    correlation_id: str | None = None


class SkipFollowUpCommand(_WsEvent):
    type: Literal["follow_up.skip"] = "follow_up.skip"
    question_id: UUID
    correlation_id: str | None = None


class AddPlaylistTrackCommand(_WsEvent):
    type: Literal["playlist.add_track"] = "playlist.add_track"
    title: str = Field(min_length=1, max_length=300)
    artist: str = Field(min_length=1, max_length=300)
    year: int | None = Field(default=None, ge=1900, le=2100)
    cover_url: str | None = None
    correlation_id: str | None = None


class RemovePlaylistTrackCommand(_WsEvent):
    type: Literal["playlist.remove_track"] = "playlist.remove_track"
    track_id: UUID
    correlation_id: str | None = None


ClientEvent = Annotated[
    Union[
        SendMessageCommand,
        AnswerFollowUpWithOptionCommand,
        AnswerFollowUpWithTextCommand,
        SkipFollowUpCommand,
        AddPlaylistTrackCommand,
        RemovePlaylistTrackCommand,
    ],
    Field(discriminator="type"),
]


class WebSocketEventCatalog(Schema):
    """References every event shape for OpenAPI client generation."""

    client_event: ClientEvent | None = Field(
        default=None,
        description="Any event the frontend may send over the socket.",
    )
    server_event: ServerEvent | None = Field(
        default=None,
        description="Any event the backend may push over the socket.",
    )
