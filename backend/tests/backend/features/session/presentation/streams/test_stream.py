import asyncio

from backend.features.session.domain import InvalidSessionPhaseTransitionError
from backend.features.session.presentation.streams.events import DoneEvent, ErrorEvent
from backend.features.session.presentation.streams.stream import session_events


def test_command_error_is_followed_by_done() -> None:
    async def failing_events():
        raise InvalidSessionPhaseTransitionError("questions unanswered")
        yield

    async def collect():
        return [event async for event in session_events(failing_events())]

    events = asyncio.run(collect())
    assert events == [
        ErrorEvent(
            code="InvalidSessionPhaseTransitionError",
            message="questions unanswered",
        ),
        DoneEvent(),
    ]


def test_unexpected_error_is_sanitized_and_followed_by_done() -> None:
    async def failing_events():
        raise RuntimeError("sensitive detail")
        yield

    async def collect():
        return [event async for event in session_events(failing_events())]

    events = asyncio.run(collect())
    assert events == [
        ErrorEvent(
            code="InternalError", message="Die Antwort konnte nicht geladen werden."
        ),
        DoneEvent(),
    ]
