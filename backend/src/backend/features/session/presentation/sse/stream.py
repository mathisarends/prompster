import logging
from collections.abc import AsyncIterator

from pydantic import TypeAdapter
from fastapi.responses import StreamingResponse

from backend.features.session.application import SessionEvent
from backend.features.session.domain import (
    InvalidSessionPhaseTransitionError,
    NoPendingToolCallSequenceError,
    PendingToolCallsError,
    ToolCallAlreadyResolvedError,
    ToolCallNotFoundError,
)
from backend.features.session.presentation.sse.events import (
    DoneEvent,
    ErrorEvent,
    ServerEvent,
    SessionEventType,
)
from backend.features.session.presentation.sse.mappers import to_server_event

_COMMAND_ERRORS = (
    InvalidSessionPhaseTransitionError,
    NoPendingToolCallSequenceError,
    PendingToolCallsError,
    ToolCallAlreadyResolvedError,
    ToolCallNotFoundError,
    ValueError,
)

_SERVER_EVENT_ADAPTER: TypeAdapter[ServerEvent] = TypeAdapter(ServerEvent)
logger = logging.getLogger(__name__)


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
    except Exception:
        # An unexpected error (e.g. while running the agent, loading an image
        # attachment, or calling the LLM) must not kill the stream silently —
        # otherwise the client receives an empty event stream with no error and
        # no done event. Log the traceback and surface a generic error event.
        logger.exception("Unexpected error while streaming session events.")
        yield _to_sse(_to_unexpected_error_event())
    yield _to_sse(DoneEvent())


# High-frequency events (one per streamed token) — logging each one floods the
# output, so we skip them in the per-event debug log.
_HIGH_FREQUENCY_EVENTS = frozenset({SessionEventType.ASSISTANT_MESSAGE_CHUNK})


def _to_sse(event: ServerEvent) -> str:
    event_name = event.type.value
    data = _SERVER_EVENT_ADAPTER.dump_json(event, by_alias=True).decode()
    if event.type not in _HIGH_FREQUENCY_EVENTS:
        logger.debug("Emitting SSE event: name=%s data=%s", event_name, data)
    return f"event: {event_name}\ndata: {data}\n\n"


def _to_error_event(error: Exception) -> ErrorEvent:
    return ErrorEvent(
        code=type(error).__name__,
        message=str(error) or type(error).__name__,
    )


def _to_unexpected_error_event() -> ErrorEvent:
    return ErrorEvent(
        code="InternalError",
        message="Die Antwort konnte nicht geladen werden.",
    )
