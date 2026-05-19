from backend.features.session.application import (
    SessionAssistantMessageChunk,
    SessionAssistantMessageCompleted,
    SessionAssistantMessageStarted,
    SessionEvent,
    SessionPlaylistSet,
    SessionPlaylistTrackAdded,
    SessionPlaylistTrackRemoved,
)
from backend.features.session.domain import (
    FollowUpQuestion,
    FollowUpQuestionGroup,
    Playlist,
    PlaylistTrack,
    SessionMessage,
    ToolCall,
    ToolCallGroup,
)
from backend.features.session.presentation.sse.events import (
    AssistantMessageChunkEvent,
    AssistantMessageCompletedEvent,
    AssistantMessageStartedEvent,
    FollowUpOptionPayload,
    FollowUpQuestionGroupPayload,
    FollowUpQuestionPayload,
    MessagePayload,
    PlaylistPayload,
    PlaylistSetEvent,
    PlaylistTrackAddedEvent,
    PlaylistTrackPayload,
    PlaylistTrackRemovedEvent,
    ServerEvent,
    ToolCallGroupPayload,
    ToolCallPayload,
    ToolFunctionPayload,
)


def to_server_event(event: SessionEvent) -> ServerEvent:
    if isinstance(event, SessionAssistantMessageStarted):
        return AssistantMessageStartedEvent(
            message_id=event.message.id,
            created_at=event.message.created_at,
        )

    if isinstance(event, SessionAssistantMessageChunk):
        return AssistantMessageChunkEvent(
            message_id=event.message_id,
            chunk=event.chunk,
        )

    if isinstance(event, SessionAssistantMessageCompleted):
        return AssistantMessageCompletedEvent(
            message=_to_message_payload(event.message),
        )

    if isinstance(event, SessionPlaylistSet):
        return PlaylistSetEvent(playlist=_to_playlist_payload(event.playlist))

    if isinstance(event, SessionPlaylistTrackAdded):
        return PlaylistTrackAddedEvent(
            playlist_id=event.playlist_id,
            track=_to_playlist_track_payload(event.track),
        )

    if isinstance(event, SessionPlaylistTrackRemoved):
        return PlaylistTrackRemovedEvent(
            playlist_id=event.playlist_id,
            track_id=event.track_id,
        )

    raise TypeError(f"Unsupported session event: {type(event).__name__}")


def _to_message_payload(message: SessionMessage) -> MessagePayload:
    return MessagePayload(
        id=message.id,
        role=message.role,
        content=message.content,
        created_at=message.created_at,
        tool_call_group=(
            _to_tool_call_group_payload(message.tool_call_group)
            if message.tool_call_group is not None
            else None
        ),
        follow_up_group=(
            _to_follow_up_group_payload(message.follow_up_group)
            if message.follow_up_group is not None
            else None
        ),
    )


def _to_tool_call_group_payload(group: ToolCallGroup) -> ToolCallGroupPayload:
    return ToolCallGroupPayload(
        id=group.id,
        calls=[_to_tool_call_payload(call) for call in group.calls],
    )


def _to_tool_call_payload(call: ToolCall) -> ToolCallPayload:
    return ToolCallPayload(
        id=call.id,
        function=ToolFunctionPayload(
            name=call.function.name,
            arguments=call.function.arguments,
        ),
        state=call.state,
        result=call.result,
        error=call.error,
    )


def _to_follow_up_group_payload(
    group: FollowUpQuestionGroup,
) -> FollowUpQuestionGroupPayload:
    return FollowUpQuestionGroupPayload(
        id=group.id,
        questions=[_to_follow_up_question_payload(q) for q in group.questions],
    )


def _to_follow_up_question_payload(
    question: FollowUpQuestion,
) -> FollowUpQuestionPayload:
    return FollowUpQuestionPayload(
        id=question.id,
        question=question.question,
        options=[
            FollowUpOptionPayload(id=option.id, label=option.label)
            for option in question.options
        ],
        state=question.state,
        answer_text=question.answer_text,
        answered_option_id=question.answered_option_id,
    )


def _to_playlist_payload(playlist: Playlist) -> PlaylistPayload:
    return PlaylistPayload(
        id=playlist.id,
        name=playlist.name,
        tracks=[_to_playlist_track_payload(track) for track in playlist.tracks],
    )


def _to_playlist_track_payload(track: PlaylistTrack) -> PlaylistTrackPayload:
    return PlaylistTrackPayload(
        id=track.id,
        title=track.title,
        artist=track.artist,
        year=track.year,
        cover_url=track.cover_url,
    )
