from datetime import datetime, timezone
from uuid import uuid4

from backend.features.session.application import (
    SessionAssistantMessageChunk,
    SessionAssistantMessageCompleted,
    SessionAssistantMessageStarted,
    SessionFollowUpGroupAdded,
    SessionToolCallSequenceAdded,
    SessionToolCallResolved,
)
from backend.features.session.domain import (
    AssistantMessage,
    FollowUpOption,
    FollowUpQuestion,
    FollowUpQuestionGroup,
    PendingCall,
    ToolCallSequence,
    ToolFunction,
)
from backend.features.session.presentation.sse.events import (
    AssistantMessageChunkEvent,
    AssistantMessageCompletedEvent,
    AssistantMessageStartedEvent,
    FollowUpGroupAddedEvent,
    SessionEventType,
    ToolCallSequenceAddedEvent,
    ToolCallResolvedEvent,
)
from backend.features.session.presentation.sse.mappers import to_server_event


def _make_assistant_message() -> AssistantMessage:
    return AssistantMessage(
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

    def test_to_server_event_maps_tool_call_sequence_added(self) -> None:
        sequence = ToolCallSequence(
            calls=[
                PendingCall(
                    id="call-1",
                    function=ToolFunction(
                        name="search_tracks",
                        arguments={"query": "abba"},
                    ),
                )
            ]
        )

        event = to_server_event(SessionToolCallSequenceAdded(sequence=sequence))

        assert isinstance(event, ToolCallSequenceAddedEvent)
        assert event.type == SessionEventType.TOOL_CALL_SEQUENCE_ADDED
        assert event.sequence.id == sequence.id
        assert event.sequence.calls[0].id == "call-1"

    def test_to_server_event_maps_tool_call_resolved(self) -> None:
        sequence_id = uuid4()

        event = to_server_event(
            SessionToolCallResolved(
                sequence_id=sequence_id,
                tool_call_id="call-1",
                result="done",
            )
        )

        assert isinstance(event, ToolCallResolvedEvent)
        assert event.type == SessionEventType.TOOL_CALL_RESOLVED
        assert event.sequence_id == sequence_id
        assert event.tool_call_id == "call-1"
        assert event.result == "done"

    def test_to_server_event_maps_follow_up_group_added(self) -> None:
        group = FollowUpQuestionGroup(
            questions=[
                FollowUpQuestion(
                    question="Welches Genre?",
                    options=[FollowUpOption(id="1", label="House")],
                )
            ]
        )

        event = to_server_event(SessionFollowUpGroupAdded(group=group))

        assert isinstance(event, FollowUpGroupAddedEvent)
        assert event.type == SessionEventType.FOLLOW_UP_GROUP_ADDED
        assert event.group.id == group.id
        assert event.group.questions[0].question == "Welches Genre?"
