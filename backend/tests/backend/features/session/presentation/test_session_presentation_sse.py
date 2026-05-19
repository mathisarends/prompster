from backend.features.session.presentation.events import (
    DoneEvent,
    SessionEventSchema,
    SessionEventType,
)
from backend.features.session.presentation.sse import to_sse


class TestSessionEventSchema:
    def test_references_only_server_events(self) -> None:
        schema = SessionEventSchema()

        assert schema.server_event is None
        assert not hasattr(schema, "client_event")


class TestServerSentEvents:
    def test_formats_done_event_with_enum_value(self) -> None:
        event = DoneEvent()

        assert event.type == SessionEventType.DONE
        assert to_sse(event) == 'event: done\ndata: {"type":"done"}\n\n'
