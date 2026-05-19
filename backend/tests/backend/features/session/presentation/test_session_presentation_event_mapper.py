from datetime import datetime, timezone
from uuid import uuid4

from backend.features.session.application import (
    SessionAssistantMessageChunk,
    SessionAssistantMessageCompleted,
    SessionAssistantMessageStarted,
)
from backend.features.session.domain import MessageRole, SessionMessage
from backend.features.session.presentation.sse.events import (
    AssistantMessageChunkEvent,
    AssistantMessageCompletedEvent,
    AssistantMessageStartedEvent,
    SessionEventType,
)
from backend.features.session.presentation.sse.mappers import to_server_event


def _make_assistant_message() -> SessionMessage:
    return SessionMessage(
        role=MessageRole.ASSISTANT,
        content="",
        id=uuid4(),
        created_time=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


class TestSessionEventMapper:
    def test_to_server_event_maps_assistant_message_started(self) -> None:
        message = _make_assistant_message()

        event = to_server_event(SessionAssistantMessageStarted(message=message))

        assert isinstance(event, AssistantMessageStartedEvent)
        assert event.type == SessionEventType.ASSISTANT_MESSAGE_STARTED
        assert event.message_id == message.id
        assert event.created_at == message.created_at

    def test_to_server_event_maps_assistant_message_chunk(self) -> None:
        message_id = uuid4()

        event = to_server_event(
            SessionAssistantMessageChunk(message_id=message_id, chunk="hello")
        )

        assert isinstance(event, AssistantMessageChunkEvent)
        assert event.type == SessionEventType.ASSISTANT_MESSAGE_CHUNK
        assert event.message_id == message_id
        assert event.chunk == "hello"

    def test_to_server_event_maps_assistant_message_completed(self) -> None:
        message = _make_assistant_message()
        message.content = "Hello world"

        event = to_server_event(SessionAssistantMessageCompleted(message=message))

        assert isinstance(event, AssistantMessageCompletedEvent)
        assert event.type == SessionEventType.ASSISTANT_MESSAGE_COMPLETED
        assert event.message.id == message.id
        assert event.message.content == "Hello world"
