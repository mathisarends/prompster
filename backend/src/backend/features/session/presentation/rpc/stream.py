import logging
from collections.abc import AsyncGenerator
from contextlib import aclosing

from backend.features.session.application import SessionEvent
from backend.features.session.domain import (
    InvalidSessionPhaseTransitionError,
    NoPendingToolCallSequenceError,
    PendingToolCallsError,
    ToolCallAlreadyResolvedError,
    ToolCallNotFoundError,
)
from backend.features.session.presentation.rpc.events import (
    DoneEvent,
    ErrorEvent,
    SessionStreamEvent,
)
from backend.features.session.presentation.rpc.mappers import to_session_stream_event

logger = logging.getLogger(__name__)


async def session_events(
    events: AsyncGenerator[SessionEvent],
) -> AsyncGenerator[SessionStreamEvent]:
    try:
        async with aclosing(events):
            async for event in events:
                yield to_session_stream_event(event)
    except _COMMAND_ERRORS as exc:
        yield ErrorEvent(
            code=type(exc).__name__, message=str(exc) or type(exc).__name__
        )
    except Exception:
        # Stream boundary: clients get a generic error event, details stay in logs.
        logger.exception("Unexpected error while streaming session events.")
        yield ErrorEvent(
            code="InternalError", message="Die Antwort konnte nicht geladen werden."
        )
    yield DoneEvent()


_COMMAND_ERRORS = (
    InvalidSessionPhaseTransitionError,
    NoPendingToolCallSequenceError,
    PendingToolCallsError,
    ToolCallAlreadyResolvedError,
    ToolCallNotFoundError,
    ValueError,
)
