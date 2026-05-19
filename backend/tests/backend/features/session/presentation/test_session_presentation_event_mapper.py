from uuid import uuid4

from backend.features.session.application import SessionTitleGenerated
from backend.features.session.presentation.sse.events import (
    SessionEventType,
    SessionTitleGeneratedEvent,
)
from backend.features.session.presentation.sse.mappers import to_server_event


class TestSessionEventMapper:
    def test_to_server_event_maps_title_generated_event(self) -> None:
        session_id = uuid4()

        event = to_server_event(
            SessionTitleGenerated(session_id=session_id, title="Roadtrip")
        )

        assert isinstance(event, SessionTitleGeneratedEvent)
        assert event.type == SessionEventType.SESSION_TITLE_GENERATED
        assert event.session_id == session_id
        assert event.title == "Roadtrip"
