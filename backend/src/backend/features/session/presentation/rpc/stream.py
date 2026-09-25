import logging
from collections.abc import AsyncIterator

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
    ServerEvent,
)
from backend.features.session.presentation.rpc.mappers import to_server_event

logger = logging.getLogger(__name__)

_COMMAND_ERRORS = (
    InvalidSessionPhaseTransitionError,
    NoPendingToolCallSequenceError,
    PendingToolCallsError,
    ToolCallAlreadyResolvedError,
    ToolCallNotFoundError,
    ValueError,
)


async def session_events(
    events: AsyncIterator[SessionEvent],
) -> AsyncIterator[ServerEvent]:
    try:
        async for event in events:
            yield to_server_event(event)
    except _COMMAND_ERRORS as exc:
        yield ErrorEvent(
            code=type(exc).__name__, message=str(exc) or type(exc).__name__
        )
    except Exception:
        logger.exception("Unexpected error while streaming session events.")
        yield ErrorEvent(
            code="InternalError", message="Die Antwort konnte nicht geladen werden."
        )
    yield DoneEvent()
