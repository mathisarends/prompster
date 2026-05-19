from backend.features.session.application.ports.session_summary_query import (
    SessionSummary,
)
from backend.features.session.domain import (
    AssistantMessage,
    CompletedCall,
    FailedCall,
    FollowUpQuestion,
    FollowUpQuestionGroup,
    PendingCall,
    PlaylistTrack,
    Session,
    SessionEntry,
    ToolCall,
    ToolCallGroup,
    UserMessage,
)
from backend.features.session.presentation.schemas import (
    AssistantMessageEntryResponse,
    FollowUpOptionResponse,
    FollowUpQuestionGroupEntryResponse,
    FollowUpQuestionResponse,
    PlaylistTrackResponse,
    SessionEntryResponse,
    SessionResponse,
    SessionSummaryResponse,
    ToolCallGroupEntryResponse,
    ToolCallResponse,
    ToolFunctionResponse,
    UserMessageEntryResponse,
)


def to_session_response(session: Session) -> SessionResponse:
    return SessionResponse(
        id=session.id,
        title=session.title,
        is_starred=session.is_starred,
        created_at=session.created_at,
        entries=[to_entry_response(entry) for entry in session.entries],
    )


def to_entry_response(entry: SessionEntry) -> SessionEntryResponse:
    if isinstance(entry, UserMessage):
        return UserMessageEntryResponse(
            id=entry.id,
            content=entry.content,
            created_at=entry.created_at,
        )
    if isinstance(entry, AssistantMessage):
        return AssistantMessageEntryResponse(
            id=entry.id,
            content=entry.content,
            created_at=entry.created_at,
        )
    if isinstance(entry, ToolCallGroup):
        return to_tool_call_group_response(entry)
    if isinstance(entry, FollowUpQuestionGroup):
        return to_follow_up_group_response(entry)
    raise TypeError(f"Unsupported session entry: {type(entry).__name__}")


def to_tool_call_group_response(group: ToolCallGroup) -> ToolCallGroupEntryResponse:
    return ToolCallGroupEntryResponse(
        id=group.id,
        created_at=group.created_at,
        calls=[to_tool_call_response(call) for call in group.calls],
    )


def to_tool_call_response(call: ToolCall) -> ToolCallResponse:
    if isinstance(call, CompletedCall):
        state, result, error = "completed", call.result, None
    elif isinstance(call, FailedCall):
        state, result, error = "failed", None, call.error
    elif isinstance(call, PendingCall):
        state, result, error = "pending", None, None
    else:
        raise TypeError(f"Unsupported tool call: {type(call).__name__}")
    return ToolCallResponse(
        id=call.id,
        function=ToolFunctionResponse(
            name=call.function.name,
            arguments=call.function.arguments,
        ),
        state=state,
        result=result,
        error=error,
    )


def to_follow_up_group_response(
    group: FollowUpQuestionGroup,
) -> FollowUpQuestionGroupEntryResponse:
    return FollowUpQuestionGroupEntryResponse(
        id=group.id,
        created_at=group.created_at,
        questions=[to_follow_up_question_response(q) for q in group.questions],
    )


def to_follow_up_question_response(
    question: FollowUpQuestion,
) -> FollowUpQuestionResponse:
    return FollowUpQuestionResponse(
        id=question.id,
        question=question.question,
        options=[
            FollowUpOptionResponse(id=option.id, label=option.label)
            for option in question.options
        ],
        state=question.state.value,
        answer_text=question.answer_text,
        answered_option_id=question.answered_option_id,
    )


def to_session_summary_response(session: SessionSummary) -> SessionSummaryResponse:
    return SessionSummaryResponse(
        id=session.id,
        title=session.title,
        is_starred=session.is_starred,
        created_at=session.created_at,
        last_activity_at=session.last_activity_at,
    )


def to_playlist_track_response(track: PlaylistTrack) -> PlaylistTrackResponse:
    return PlaylistTrackResponse(
        id=track.id,
        title=track.title,
        artist=track.artist,
        year=track.year,
        cover_url=track.cover_url,
    )
