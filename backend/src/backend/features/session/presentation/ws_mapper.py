from backend.features.session.domain import (
    FollowUpQuestion,
    FollowUpQuestionGroup,
    Playlist,
    PlaylistTrack,
    Session,
    SessionMessage,
    ToolCall,
    ToolCallGroup,
)
from backend.features.session.presentation.ws_events import (
    FollowUpOptionPayload,
    FollowUpQuestionGroupPayload,
    FollowUpQuestionPayload,
    MessagePayload,
    PlaylistPayload,
    PlaylistTrackPayload,
    SessionSnapshotPayload,
    ToolCallGroupPayload,
    ToolCallPayload,
    ToolFunctionPayload,
)


def to_session_snapshot_payload(session: Session) -> SessionSnapshotPayload:
    return SessionSnapshotPayload(
        id=session.id,
        title=session.title,
        created_at=session.created_at,
        messages=[to_message_payload(message) for message in session.messages],
        playlist=(
            to_playlist_payload(session.playlist)
            if session.playlist is not None
            else None
        ),
    )


def to_message_payload(message: SessionMessage) -> MessagePayload:
    return MessagePayload(
        id=message.id,
        role=message.role,
        content=message.content,
        created_at=message.created_at,
        tool_call_group=(
            to_tool_call_group_payload(message.tool_call_group)
            if message.tool_call_group is not None
            else None
        ),
        follow_up_group=(
            to_follow_up_group_payload(message.follow_up_group)
            if message.follow_up_group is not None
            else None
        ),
    )


def to_tool_call_group_payload(group: ToolCallGroup) -> ToolCallGroupPayload:
    return ToolCallGroupPayload(
        id=group.id,
        calls=[to_tool_call_payload(call) for call in group.calls],
    )


def to_tool_call_payload(call: ToolCall) -> ToolCallPayload:
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


def to_follow_up_group_payload(
    group: FollowUpQuestionGroup,
) -> FollowUpQuestionGroupPayload:
    return FollowUpQuestionGroupPayload(
        id=group.id,
        questions=[to_follow_up_question_payload(q) for q in group.questions],
    )


def to_follow_up_question_payload(
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


def to_playlist_payload(playlist: Playlist) -> PlaylistPayload:
    return PlaylistPayload(
        id=playlist.id,
        name=playlist.name,
        tracks=[to_playlist_track_payload(track) for track in playlist.tracks],
    )


def to_playlist_track_payload(track: PlaylistTrack) -> PlaylistTrackPayload:
    return PlaylistTrackPayload(
        id=track.id,
        title=track.title,
        artist=track.artist,
        year=track.year,
        cover_url=track.cover_url,
    )
