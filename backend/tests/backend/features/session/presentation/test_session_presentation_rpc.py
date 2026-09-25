import asyncio
from typing import get_args

from backend.features.session.domain import InvalidSessionPhaseTransitionError
from backend.features.session.presentation.rpc.events import (
    DoneEvent,
    ErrorEvent,
    PlaylistPayload,
    ServerEvent,
    SessionSnapshotPayload,
    _SessionEventSchema,
)
from backend.features.session.presentation.rpc.stream import session_events


def test_event_union_has_discriminated_model_members() -> None:
    event_classes = get_args(get_args(ServerEvent.__value__)[0])
    assert all(issubclass(cls, _SessionEventSchema) for cls in event_classes)
    assert "type" not in PlaylistPayload.model_fields
    assert "type" not in SessionSnapshotPayload.model_fields


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
