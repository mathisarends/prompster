from dataclasses import dataclass
from uuid import uuid4

from agent.agent import (
    AssistantMessageChunkEvent,
    AssistantMessageEvent,
    FollowUpRequestedEvent,
    ToolCallEvent,
    ToolResultEvent,
    WorkspaceUpdatedEvent,
)
from agent.playlist import (
    PlaylistDraft,
    PlaylistDraftTrack,
    PlaylistDraftTrackReplacement,
    PlaylistDraftTracksAdded,
    PlaylistDraftTracksRemoved,
    PlaylistDraftTracksReplaced,
)
from agent.tools.views import AskFollowUpOption, AskFollowUpQuestion

from backend.features.session.application.ports.session_runner import (
    SessionRunnerAssistantMessage,
    SessionRunnerAssistantMessageChunk,
    SessionRunnerFollowUpRequested,
    SessionRunnerPlaylistTracksAdded,
    SessionRunnerPlaylistTracksRemoved,
    SessionRunnerPlaylistTracksReplaced,
    SessionRunnerPlaylistUpdated,
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
                status_label="Adding tracks…",
                action_type=None,
            )
        )

        assert len(result) == 1
        event = result[0]
        assert isinstance(event, SessionRunnerToolCallStarted)
        assert event.call.id == "call_1"
        assert event.call.function.name == "add_tracks"
        assert event.call.function.arguments == {"query": "80s synth"}
        assert event.call.function.status_label == "Adding tracks…"
        assert event.call.function.action_type is None

    def test_unknown_action_type_string_becomes_none(self) -> None:
        # Defensive: a future agent release may invent a new action_type
        # we don't know yet — we must not crash the stream.
        mapper = AgentSessionEventMapper()

        result = mapper.map(
            ToolCallEvent(
                tool_call_id="call_x",
                name="mystery",
                args={},
                action_type="not_a_real_action_type",  # type: ignore[arg-type]
            )
        )

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


class TestFollowUpMapping:
    def test_follow_up_questions_get_1_indexed_option_ids(self) -> None:
        # The agent doesn't ship option ids — the runner assigns "1", "2", …
        # in render order so the frontend can echo a stable selection back.
        mapper = AgentSessionEventMapper()

        result = mapper.map(
            FollowUpRequestedEvent(
                tool_call_id="call_followup",
                questions=[
                    AskFollowUpQuestion(
                        question="Welche Stimmung?",
                        options=[
                            AskFollowUpOption(label="tanzbar"),
                            AskFollowUpOption(label="chillig"),
                        ],
                    )
                ],
            )
        )

        assert len(result) == 1
        event = result[0]
        assert isinstance(event, SessionRunnerFollowUpRequested)
        assert len(event.questions) == 1
        assert event.questions[0].question == "Welche Stimmung?"
        assert [o.id for o in event.questions[0].options] == ["1", "2"]
        assert [o.label for o in event.questions[0].options] == ["tanzbar", "chillig"]


class TestWorkspaceUpdateMapping:
    def _draft(
        self, *, tracks: list[PlaylistDraftTrack] | None = None
    ) -> PlaylistDraft:
        return PlaylistDraft(name="Deck", tracks=tracks or [])

    def test_tracks_added_propagates_playlist_id_and_tracks(self) -> None:
        mapper = AgentSessionEventMapper()
        draft = self._draft()
        added = PlaylistDraftTrack(title="Umbrella", artist="Rihanna", year=2007)

        result = mapper.map(
            WorkspaceUpdatedEvent(
                playlist_draft=draft,
                update=PlaylistDraftTracksAdded(playlist_draft=draft, tracks=[added]),
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
            WorkspaceUpdatedEvent(
                playlist_draft=draft,
                update=PlaylistDraftTracksRemoved(
                    playlist_draft=draft, track_ids=[removed_id]
                ),
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
        replacement_track = PlaylistDraftTrack(title="New", artist="Artist", year=2020)

        result = mapper.map(
            WorkspaceUpdatedEvent(
                playlist_draft=draft,
                update=PlaylistDraftTracksReplaced(
                    playlist_draft=draft,
                    replacements=[
                        PlaylistDraftTrackReplacement(
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

    def test_unknown_workspace_update_falls_back_to_full_playlist_snapshot(
        self,
    ) -> None:
        # The mapper has explicit cases for added/removed/replaced and treats
        # anything else as "I don't know what changed — resend the whole
        # playlist." This is the safety net that keeps the frontend in sync
        # if the agent introduces a new update variant.
        @dataclass
        class _UnknownUpdate:
            pass

        mapper = AgentSessionEventMapper()
        track = PlaylistDraftTrack(title="Take On Me", artist="a-ha", year=1985)
        draft = self._draft(tracks=[track])

        result = mapper.map(
            WorkspaceUpdatedEvent(playlist_draft=draft, update=_UnknownUpdate())  # type: ignore[arg-type]
        )

        assert len(result) == 1
        event = result[0]
        assert isinstance(event, SessionRunnerPlaylistUpdated)
        assert event.playlist.id == draft.id
        assert event.playlist.name == draft.name
        assert [t.title for t in event.playlist.tracks] == ["Take On Me"]


class TestUnknownEvent:
    def test_unknown_event_type_yields_no_runner_events(self) -> None:
        # The mapper must never crash on an unexpected event. The runner's
        # loop relies on getting back an iterable — empty list means
        # "ignore and keep streaming".
        mapper = AgentSessionEventMapper()

        result = mapper.map(object())

        assert result == []
