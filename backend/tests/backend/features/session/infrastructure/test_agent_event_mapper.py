from uuid import uuid4

from agent.agent import (
    AssistantMessageChunkEvent,
    AssistantMessageEvent,
    DeckUpdatedEvent,
    QuestionAskedEvent,
    SuspendedForUserInputEvent,
    ToolCallEvent,
    ToolResultEvent,
)
from agent.deck import (
    DeckDraft,
    DeckDraftCreated,
    DeckDraftTrack,
    DeckDraftTrackReplacement,
    DeckDraftTracksAdded,
    DeckDraftTracksRemoved,
    DeckDraftTracksReplaced,
)

from backend.features.session.application.ports.session_runner import (
    SessionRunnerAssistantMessage,
    SessionRunnerAssistantMessageChunk,
    SessionRunnerPlaylistTracksAdded,
    SessionRunnerPlaylistTracksRemoved,
    SessionRunnerPlaylistTracksReplaced,
    SessionRunnerPlaylistUpdated,
    SessionRunnerQuestionAsked,
    SessionRunnerSuspendedForInput,
    SessionRunnerToolCallCompleted,
    SessionRunnerToolCallStarted,
)
from backend.features.session.domain import ToolActionType
from backend.features.session.infrastructure.agent_event_mapper import (
    AgentSessionEventMapper,
)


class TestAssistantMessageMapping:
    def test_assistant_chunk_event_maps_to_chunk(self) -> None:
        mapper = AgentSessionEventMapper()

        result = mapper.map(AssistantMessageChunkEvent(chunk="hel"))

        assert result == [SessionRunnerAssistantMessageChunk(chunk="hel")]

    def test_assistant_message_event_maps_to_final_message(self) -> None:
        mapper = AgentSessionEventMapper()

        result = mapper.map(AssistantMessageEvent(content="hello world"))

        assert result == [SessionRunnerAssistantMessage(content="hello world")]


class TestToolCallMapping:
    def test_tool_call_event_carries_arguments_and_status_label(self) -> None:
        mapper = AgentSessionEventMapper()

        result = mapper.map(
            ToolCallEvent(
                tool_call_id="call_1",
                name="add_tracks",
                args={"query": "80s synth"},
                status_label="Adding tracks...",
                action_type=None,
                is_onboarding_question=True,
            )
        )

        assert len(result) == 1
        event = result[0]
        assert isinstance(event, SessionRunnerToolCallStarted)
        assert event.call.id == "call_1"
        assert event.call.function.name == "add_tracks"
        assert event.call.function.arguments == {"query": "80s synth"}
        assert event.call.function.status_label == "Adding tracks..."
        assert event.call.function.action_type is None
        assert event.call.function.is_onboarding_question is True

    def test_unknown_action_type_string_becomes_none(self) -> None:
        mapper = AgentSessionEventMapper()

        # ``model_construct`` bypasses validation so we can simulate a malformed
        # or drifted event whose ``action_type`` the backend's ``ToolActionType``
        # does not recognise — the mapper must coerce it to None.
        event = ToolCallEvent.model_construct(
            tool_call_id="call_x",
            name="mystery",
            args={},
            status_label=None,
            action_type="not_a_real_action_type",
        )

        result = mapper.map(event)

        assert isinstance(result[0], SessionRunnerToolCallStarted)
        assert result[0].call.function.action_type is None

    def test_known_action_type_value_is_translated_to_enum(self) -> None:
        mapper = AgentSessionEventMapper()
        known_value = next(iter(ToolActionType)).value

        result = mapper.map(
            ToolCallEvent(
                tool_call_id="call_y",
                name="x",
                args={},
                action_type=known_value,  # type: ignore[arg-type]
            )
        )

        assert isinstance(result[0], SessionRunnerToolCallStarted)
        assert result[0].call.function.action_type == ToolActionType(known_value)

    def test_tool_result_event_maps_to_completed(self) -> None:
        mapper = AgentSessionEventMapper()

        result = mapper.map(
            ToolResultEvent(tool_call_id="call_1", name="add_tracks", result="ok")
        )

        assert result == [
            SessionRunnerToolCallCompleted(tool_call_id="call_1", result="ok")
        ]


class TestWorkspaceUpdateMapping:
    def _draft(self, *, tracks: list[DeckDraftTrack] | None = None) -> DeckDraft:
        return DeckDraft(name="Deck", tracks=tracks or [])

    def test_tracks_added_propagates_playlist_id_and_tracks(self) -> None:
        mapper = AgentSessionEventMapper()
        draft = self._draft()
        added = DeckDraftTrack(title="Umbrella", artist="Rihanna", year=2007)

        result = mapper.map(
            DeckUpdatedEvent(
                deck_draft=draft,
                update=DeckDraftTracksAdded(deck_draft=draft, tracks=[added]),
            )
        )

        assert len(result) == 1
        event = result[0]
        assert isinstance(event, SessionRunnerPlaylistTracksAdded)
        assert event.playlist_id == draft.id
        assert len(event.tracks) == 1
        assert event.tracks[0].title == "Umbrella"
        assert event.tracks[0].artist == "Rihanna"
        assert event.tracks[0].year == 2007

    def test_tracks_removed_propagates_ids(self) -> None:
        mapper = AgentSessionEventMapper()
        draft = self._draft()
        removed_id = uuid4()

        result = mapper.map(
            DeckUpdatedEvent(
                deck_draft=draft,
                update=DeckDraftTracksRemoved(deck_draft=draft, track_ids=[removed_id]),
            )
        )

        assert result == [
            SessionRunnerPlaylistTracksRemoved(
                playlist_id=draft.id, track_ids=[removed_id]
            )
        ]

    def test_tracks_replaced_maps_each_replacement_to_session_track(self) -> None:
        mapper = AgentSessionEventMapper()
        draft = self._draft()
        original_id = uuid4()
        replacement_track = DeckDraftTrack(title="New", artist="Artist", year=2020)

        result = mapper.map(
            DeckUpdatedEvent(
                deck_draft=draft,
                update=DeckDraftTracksReplaced(
                    deck_draft=draft,
                    replacements=[
                        DeckDraftTrackReplacement(
                            track_id=original_id, track=replacement_track
                        )
                    ],
                ),
            )
        )

        assert len(result) == 1
        event = result[0]
        assert isinstance(event, SessionRunnerPlaylistTracksReplaced)
        assert event.playlist_id == draft.id
        assert len(event.replacements) == 1
        assert event.replacements[0].track_id == original_id
        assert event.replacements[0].track.title == "New"
        assert event.replacements[0].track.artist == "Artist"

    def test_non_incremental_update_falls_back_to_full_playlist_snapshot(
        self,
    ) -> None:
        mapper = AgentSessionEventMapper()
        track = DeckDraftTrack(title="Take On Me", artist="a-ha", year=1985)
        draft = self._draft(tracks=[track])

        result = mapper.map(
            DeckUpdatedEvent(
                deck_draft=draft,
                update=DeckDraftCreated(deck_draft=draft),
            )
        )

        assert len(result) == 1
        event = result[0]
        assert isinstance(event, SessionRunnerPlaylistUpdated)
        assert event.playlist.id == draft.id
        assert event.playlist.name == draft.name
        assert [track.title for track in event.playlist.tracks] == ["Take On Me"]


class TestUnknownEvent:
    def test_unknown_event_type_yields_no_runner_events(self) -> None:
        mapper = AgentSessionEventMapper()

        result = mapper.map(object())

        assert result == []


class TestSuspendedForInputMapping:
    def test_question_asked_event_maps_to_runner_event(self) -> None:
        mapper = AgentSessionEventMapper()

        result = mapper.map(
            QuestionAskedEvent(
                question="Fuer wen ist die Playlist?",
                hint="Enge Zielgruppen machen das Deck spitzer.",
                options=["Freunde", "Familie"],
            )
        )

        assert result == [
            SessionRunnerQuestionAsked(
                question="Fuer wen ist die Playlist?",
                hint="Enge Zielgruppen machen das Deck spitzer.",
                options=["Freunde", "Familie"],
            )
        ]

    def test_suspended_event_maps_to_runner_event(self) -> None:
        mapper = AgentSessionEventMapper()

        result = mapper.map(
            SuspendedForUserInputEvent(
                question="Fuer wen ist die Playlist?",
                hint="Enge Zielgruppen machen das Deck spitzer.",
                options=["Freunde", "Familie"],
                is_last_question=True,
            )
        )

        assert result == [
            SessionRunnerSuspendedForInput(
                question="Fuer wen ist die Playlist?",
                hint="Enge Zielgruppen machen das Deck spitzer.",
                options=["Freunde", "Familie"],
                is_last_question=True,
            )
        ]
