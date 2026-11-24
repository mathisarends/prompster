from uuid import UUID

from agent import (
    ActionType,
    AssistantRepliedEvent,
    Deck,
    DeckCreatedEvent,
    DeckTrack,
    DeckTracksAddedEvent,
    DeckTracksRemovedEvent,
    DeckTracksReplacedEvent,
    FoundTrack,
    QuestionAskedEvent,
    SelectionMode,
    ToolCallAnnouncedEvent,
    TrackReplacement,
    TracksFoundEvent,
)
from harnessed import SessionStatus
from harnessed.events import (
    CompactionFinishedEvent,
    CompactionStartedEvent,
    SessionStatusChangedEvent,
    TextDeltaEvent,
    ToolCallFinishedEvent,
)
from harnessed.events.compaction import CompactionOutcome
from harnessed.events.completion import TurnResultEvent
from harnessed.models import StopReason, ToolCall, ToolResult
from harnessed import RunResult

from backend.features.session.application.ports.session_runner import (
    SessionRunnerAssistantMessage,
    SessionRunnerAssistantMessageChunk,
    SessionRunnerCancelled,
    SessionRunnerContextCompacted,
    SessionRunnerPlaylistTracksAdded,
    SessionRunnerPlaylistTracksRemoved,
    SessionRunnerPlaylistTracksReplaced,
    SessionRunnerPlaylistUpdated,
    SessionRunnerQuestionAsked,
    SessionRunnerRunStatusChanged,
    SessionRunnerSuspendedForInput,
    SessionRunnerToolCallCompleted,
    SessionRunnerToolCallSequenceStarted,
    SessionRunnerToolCallStarted,
)
from backend.features.session.domain import RunStatus, ToolActionType
from backend.features.session.infrastructure.agent_event_mapper import (
    AgentRunEventMapper,
)

_DECK_ID = str(UUID(int=1))
_TRACK_ID = str(UUID(int=2))
_SEARCH = ToolCall("search_tracks", {"query": "a-ha"}, id="call-1")


def _track(track_id: str = _TRACK_ID) -> DeckTrack:
    return DeckTrack(id=track_id, title="Take On Me", artist="a-ha", year=1985)


def _finished(call: ToolCall, text: str = "ok") -> ToolCallFinishedEvent:
    return ToolCallFinishedEvent(call=call, result=ToolResult(text))


def _turn_result(stop_reason: StopReason) -> TurnResultEvent[None]:
    return TurnResultEvent(
        result=RunResult(text="", events=(), stop_reason=stop_reason)
    )


def test_text_deltas_and_replies_map_to_assistant_messages() -> None:
    mapper = AgentRunEventMapper()

    events = [
        *mapper.map(TextDeltaEvent(message_id="m1", text="Hal")),
        *mapper.map(TextDeltaEvent(message_id="m1", text="")),
        *mapper.map(AssistantRepliedEvent(message_id="m1", text="Hallo", final=True)),
    ]

    assert events == [
        SessionRunnerAssistantMessageChunk(chunk="Hal"),
        SessionRunnerAssistantMessage(content="Hallo"),
    ]


def test_announced_call_starts_a_labelled_tool_call() -> None:
    mapper = AgentRunEventMapper()

    events = mapper.map(
        ToolCallAnnouncedEvent(
            call=_SEARCH,
            status_label="Suche Tracks: a-ha",
            batch_label="Recherche",
            action_type=ActionType.SEARCH_TRACKS,
        )
    )

    assert events[0] == SessionRunnerToolCallSequenceStarted(label="Recherche")
    started = events[1]
    assert isinstance(started, SessionRunnerToolCallStarted)
    assert started.call.id == "call-1"
    assert dict(started.call.function.arguments) == {"query": "a-ha"}
    assert started.call.function.status_label == "Suche Tracks: a-ha"
    assert started.call.function.action_type is ToolActionType.SEARCH_TRACKS


def test_finished_call_carries_the_previews_its_tool_found() -> None:
    mapper = AgentRunEventMapper()
    tracks = tuple(
        FoundTrack(uri=f"spotify:track:{index}", title=f"Song {index}", artist="a-ha")
        for index in range(12)
    )
    mapper.map(ToolCallAnnouncedEvent(call=_SEARCH))
    mapper.map(TracksFoundEvent(call_id="call-1", tracks=tracks))

    [completed] = mapper.map(_finished(_SEARCH, "<track />"))

    assert isinstance(completed, SessionRunnerToolCallCompleted)
    assert completed.result == "<track />"
    assert len(completed.items) == 10
    assert completed.items[0].track_uri == "spotify:track:0"


def test_calls_the_ui_never_showed_finish_silently() -> None:
    question = ToolCall("ask_onboarding_question", {}, id="call-q")

    assert AgentRunEventMapper().map(_finished(question)) == []


def test_deck_events_map_to_playlist_changes() -> None:
    mapper = AgentRunEventMapper()
    replacement = _track(str(UUID(int=3)))

    [created] = mapper.map(
        DeckCreatedEvent(deck=Deck(id=_DECK_ID, name="Deck", tracks=(_track(),)))
    )
    [added] = mapper.map(DeckTracksAddedEvent(deck_id=_DECK_ID, tracks=(_track(),)))
    [removed] = mapper.map(
        DeckTracksRemovedEvent(deck_id=_DECK_ID, track_ids=(_TRACK_ID,))
    )
    [replaced] = mapper.map(
        DeckTracksReplacedEvent(
            deck_id=_DECK_ID,
            replacements=(TrackReplacement(track_id=_TRACK_ID, track=replacement),),
        )
    )

    assert isinstance(created, SessionRunnerPlaylistUpdated)
    assert created.playlist.id == UUID(_DECK_ID)
    assert isinstance(added, SessionRunnerPlaylistTracksAdded)
    assert added.tracks[0].id == UUID(_TRACK_ID)
    assert isinstance(removed, SessionRunnerPlaylistTracksRemoved)
    assert removed.track_ids == [UUID(_TRACK_ID)]
    assert isinstance(replaced, SessionRunnerPlaylistTracksReplaced)
    assert replaced.replacements[0].track.id == UUID(int=3)


def test_only_the_last_onboarding_question_suspends_the_run() -> None:
    mapper = AgentRunEventMapper()

    def ask(*, is_last: bool) -> object:
        [event] = mapper.map(
            QuestionAskedEvent(
                question="Fuer wen?",
                options=("Freunde", "Familie"),
                selection_mode=SelectionMode.MULTI_SELECT,
                is_last_question=is_last,
            )
        )
        return event

    asked = ask(is_last=False)
    suspended = ask(is_last=True)

    assert isinstance(asked, SessionRunnerQuestionAsked)
    assert isinstance(suspended, SessionRunnerSuspendedForInput)
    assert suspended.options == ["Freunde", "Familie"]
    assert suspended.is_last_question is True


def test_compaction_reports_its_status_and_result() -> None:
    mapper = AgentRunEventMapper()

    started = mapper.map(CompactionStartedEvent("c1", before_tokens=900))
    finished = mapper.map(
        CompactionFinishedEvent(
            "c1",
            CompactionOutcome.APPLIED,
            before_tokens=900,
            after_tokens=200,
        )
    )

    assert started == [SessionRunnerRunStatusChanged(status=RunStatus.COMPACTING)]
    assert finished == [
        SessionRunnerContextCompacted(tokens_before=900, tokens_after=200),
        SessionRunnerRunStatusChanged(status=RunStatus.RUNNING),
    ]


def test_pause_and_resume_change_the_run_status_once() -> None:
    mapper = AgentRunEventMapper()

    def status(value: SessionStatus) -> list[object]:
        return list(mapper.map(SessionStatusChangedEvent(status=value)))

    assert status(SessionStatus.RUNNING) == []
    assert status(SessionStatus.PAUSED) == [
        SessionRunnerRunStatusChanged(status=RunStatus.PAUSED)
    ]
    assert status(SessionStatus.RUNNING) == [
        SessionRunnerRunStatusChanged(status=RunStatus.RUNNING)
    ]
    assert status(SessionStatus.IDLE) == []


def test_only_interrupted_turns_are_cancelled() -> None:
    mapper = AgentRunEventMapper()

    assert mapper.map(_turn_result(StopReason.END)) == []
    assert mapper.map(_turn_result(StopReason.ABORTED)) == [SessionRunnerCancelled()]
    assert mapper.map(_turn_result(StopReason.STOPPED)) == [SessionRunnerCancelled()]
