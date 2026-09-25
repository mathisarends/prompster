from datetime import datetime, timezone
from uuid import uuid4

from backend.features.session.application import (
    SessionAssistantMessageChunk,
    SessionAssistantMessageCancelled,
    SessionAssistantMessageCompleted,
    SessionAssistantMessageStarted,
    SessionContextCompacted,
    SessionOnboardingQuestionAsked,
    SessionPlaylistSet,
    SessionPlaylistTrackAdded,
    SessionPlaylistTrackRemoved,
    SessionPlaylistTrackReplaced,
    SessionSuspendedForInput,
    SessionToolCallSequenceAdded,
    SessionToolCallResolved,
)
from backend.features.session.domain import (
    AssistantMessage,
    PendingCall,
    Playlist,
    PlaylistTrack,
    ToolActionType,
    ToolCallSequence,
    ToolFunction,
)
from backend.features.session.presentation.rpc.events import (
    AssistantMessageChunkEvent,
    AssistantMessageCancelledEvent,
    AssistantMessageCompletedEvent,
    AssistantMessageStartedEvent,
    ContextCompactedEvent,
    PlaylistSetEvent,
    PlaylistTrackAddedEvent,
    PlaylistTrackRemovedEvent,
    PlaylistTrackReplacedEvent,
    OnboardingQuestionAskedEvent,
    SessionEventType,
    SuspendedForInputEvent,
    ToolCallSequenceAddedEvent,
    ToolCallResolvedEvent,
)
from backend.features.session.presentation.rpc.mappers import to_server_event


def _make_assistant_message() -> AssistantMessage:
    return AssistantMessage.restore(
        content="",
        id=uuid4(),
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
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

    def test_to_server_event_maps_assistant_message_cancelled(self) -> None:
        message_id = uuid4()

        event = to_server_event(SessionAssistantMessageCancelled(message_id=message_id))

        assert isinstance(event, AssistantMessageCancelledEvent)
        assert event.type == SessionEventType.ASSISTANT_MESSAGE_CANCELLED
        assert event.message_id == message_id

    def test_to_server_event_maps_tool_call_sequence_added(self) -> None:
        sequence = ToolCallSequence.create(
            calls=[
                PendingCall(
                    id="call-1",
                    function=ToolFunction(
                        name="search_tracks",
                        arguments={"query": "abba"},
                        action_type=ToolActionType.SEARCH_TRACKS,
                    ),
                )
            ]
        )

        event = to_server_event(SessionToolCallSequenceAdded(sequence=sequence))

        assert isinstance(event, ToolCallSequenceAddedEvent)
        assert event.type == SessionEventType.TOOL_CALL_SEQUENCE_ADDED
        assert event.sequence.id == sequence.id
        assert event.sequence.calls[0].id == "call-1"
        assert event.sequence.calls[0].function.action_type == "search_tracks"

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

    def test_to_server_event_maps_context_compacted(self) -> None:
        event = to_server_event(
            SessionContextCompacted(
                reason="reactive",
                tokens_before=275000,
                compacted_tool_results=3,
            )
        )

        assert isinstance(event, ContextCompactedEvent)
        assert event.type == SessionEventType.CONTEXT_COMPACTED
        assert event.reason == "reactive"
        assert event.tokens_before == 275000
        assert event.compacted_tool_results == 3

    def test_to_server_event_maps_playlist_set(self) -> None:
        playlist = Playlist.create(
            name="80er Party",
            tracks=[PlaylistTrack.create(title="Take On Me", artist="a-ha", year=1985)],
        )

        event = to_server_event(SessionPlaylistSet(playlist=playlist))

        assert isinstance(event, PlaylistSetEvent)
        assert event.type == SessionEventType.PLAYLIST_SET
        assert event.playlist.id == playlist.id
        assert event.playlist.name == "80er Party"
        assert event.playlist.tracks[0].title == "Take On Me"

    def test_to_server_event_maps_playlist_track_added(self) -> None:
        playlist_id = uuid4()
        track = PlaylistTrack.create(
            title="Billie Jean",
            artist="Michael Jackson",
            year=1982,
        )

        event = to_server_event(
            SessionPlaylistTrackAdded(playlist_id=playlist_id, track=track)
        )

        assert isinstance(event, PlaylistTrackAddedEvent)
        assert event.type == SessionEventType.PLAYLIST_TRACK_ADDED
        assert event.playlist_id == playlist_id
        assert event.track.id == track.id

    def test_to_server_event_maps_playlist_track_removed(self) -> None:
        playlist_id = uuid4()
        track_id = uuid4()

        event = to_server_event(
            SessionPlaylistTrackRemoved(playlist_id=playlist_id, track_id=track_id)
        )

        assert isinstance(event, PlaylistTrackRemovedEvent)
        assert event.type == SessionEventType.PLAYLIST_TRACK_REMOVED
        assert event.playlist_id == playlist_id
        assert event.track_id == track_id

    def test_to_server_event_maps_playlist_track_replaced(self) -> None:
        playlist_id = uuid4()
        track_id = uuid4()
        track = PlaylistTrack.create(title="Africa", artist="Toto", year=1982)

        event = to_server_event(
            SessionPlaylistTrackReplaced(
                playlist_id=playlist_id,
                track_id=track_id,
                track=track,
            )
        )

        assert isinstance(event, PlaylistTrackReplacedEvent)
        assert event.type == SessionEventType.PLAYLIST_TRACK_REPLACED
        assert event.playlist_id == playlist_id
        assert event.track_id == track_id
        assert event.track.id == track.id

    def test_to_server_event_maps_suspended_for_input(self) -> None:
        event = to_server_event(
            SessionSuspendedForInput(
                kind="onboarding_question",
                question="Fuer wen ist die Playlist?",
                hint="Enge Zielgruppen machen das Deck spitzer.",
                options=["Freunde", "Familie"],
                question_id=uuid4(),
                is_last_question=True,
            )
        )

        assert isinstance(event, SuspendedForInputEvent)
        assert event.type == SessionEventType.SUSPENDED_FOR_INPUT
        assert event.kind == "onboarding_question"
        assert event.question == "Fuer wen ist die Playlist?"
        assert event.hint == "Enge Zielgruppen machen das Deck spitzer."
        assert event.is_last_question is True

    def test_to_server_event_maps_onboarding_question_asked(self) -> None:
        question_id = uuid4()

        event = to_server_event(
            SessionOnboardingQuestionAsked(
                question="Fuer wen ist die Playlist?",
                hint="Enge Zielgruppen machen das Deck spitzer.",
                options=["Freunde", "Familie"],
                question_id=question_id,
            )
        )

        assert isinstance(event, OnboardingQuestionAskedEvent)
        assert event.type == SessionEventType.ONBOARDING_QUESTION_ASKED
        assert event.question == "Fuer wen ist die Playlist?"
        assert event.hint == "Enge Zielgruppen machen das Deck spitzer."
        assert event.options == ["Freunde", "Familie"]
        assert event.question_id == question_id
