from uuid import uuid4

from backend.features.session.application import SessionTitleGenerated
from backend.features.session.presentation.ws.event_mapper import to_server_event
from backend.features.session.presentation.ws.events import SessionTitleGeneratedEvent


class TestWebSocketEventMapper:
    def test_to_server_event_maps_title_generated_event(self) -> None:
        session_id = uuid4()

        event = to_server_event(
            SessionTitleGenerated(session_id=session_id, title="Roadtrip")
        )

        assert isinstance(event, SessionTitleGeneratedEvent)
        assert event.session_id == session_id
        assert event.title == "Roadtrip"
