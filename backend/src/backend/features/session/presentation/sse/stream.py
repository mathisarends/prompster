from collections.abc import AsyncIterator

from pydantic import TypeAdapter
from fastapi.responses import StreamingResponse

from backend.features.session.application import SessionEvent
from backend.features.session.domain import (
    EmptyFollowUpAnswerError,
    FollowUpOptionNotFoundError,
    FollowUpQuestionAlreadyResolvedError,
    FollowUpQuestionNotFoundError,
    FollowUpQuestionOutOfOrderError,
    NoPendingFollowUpGroupError,
    NoPendingToolCallSequenceError,
    PendingFollowUpQuestionsError,
    PendingToolCallsError,
    ToolCallAlreadyResolvedError,
    ToolCallNotFoundError,
)
from backend.features.session.presentation.sse.events import (
    DoneEvent,
    ErrorEvent,
    ServerEvent,
)
from backend.features.session.presentation.sse.mappers import to_server_event

_COMMAND_ERRORS = (
    EmptyFollowUpAnswerError,
    FollowUpOptionNotFoundError,
    FollowUpQuestionAlreadyResolvedError,
    FollowUpQuestionNotFoundError,
    FollowUpQuestionOutOfOrderError,
    NoPendingFollowUpGroupError,
    NoPendingToolCallSequenceError,
    PendingFollowUpQuestionsError,
    PendingToolCallsError,
    ToolCallAlreadyResolvedError,
    ToolCallNotFoundError,
)

_SERVER_EVENT_ADAPTER: TypeAdapter[ServerEvent] = TypeAdapter(ServerEvent)


def stream_session_events(events: AsyncIterator[SessionEvent]) -> StreamingResponse:
    return StreamingResponse(
        _stream(events),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


async def _stream(events: AsyncIterator[SessionEvent]) -> AsyncIterator[str]:
    try:
        async for event in events:
            yield _to_sse(to_server_event(event))
    except _COMMAND_ERRORS as exc:
        yield _to_sse(_to_error_event(exc))
    yield _to_sse(DoneEvent())


def _to_sse(event: ServerEvent) -> str:
    event_name = getattr(event.type, "value", event.type)
    data = _SERVER_EVENT_ADAPTER.dump_json(event, by_alias=True).decode()
    return f"event: {event_name}\ndata: {data}\n\n"


def _to_error_event(error: Exception) -> ErrorEvent:
    return ErrorEvent(
        code=type(error).__name__,
        message=str(error) or type(error).__name__,
    )
