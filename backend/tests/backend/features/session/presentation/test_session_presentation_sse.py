import asyncio

from backend.features.session.domain import InvalidSessionPhaseTransitionError
from backend.features.session.presentation.sse import SessionEventSchema
from backend.features.session.presentation.sse.events import (
    DoneEvent,
    SessionEventType,
)
from backend.features.session.presentation.sse.stream import _stream, _to_sse


class TestSessionEventSchema:
    def test_references_only_server_events(self) -> None:
        schema = SessionEventSchema()

        assert schema.server_event is None
        assert not hasattr(schema, "client_event")


class TestServerSentEvents:
    def test_formats_done_event_with_enum_value(self) -> None:
        event = DoneEvent()

        assert event.type == SessionEventType.DONE
        assert _to_sse(event) == 'event: done\ndata: {"type":"done"}\n\n'

    def test_emits_error_event_when_onboarding_cannot_be_completed(self) -> None:
        async def _events():
            raise InvalidSessionPhaseTransitionError("questions unanswered")
            yield

        async def _collect() -> list[str]:
            return [event async for event in _stream(_events())]

        events = asyncio.run(_collect())

        assert events == [
            'event: error\ndata: {"type":"error","code":"InvalidSessionPhaseTransitionError","message":"questions unanswered","correlationId":null}\n\n',
            'event: done\ndata: {"type":"done"}\n\n',
        ]
