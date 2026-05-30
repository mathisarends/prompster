from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest

from backend.features.session.domain.exceptions import (
    ArtistReferenceNotFoundError,
    InvalidSessionPhaseTransitionError,
    NoCurrentAssistantMessageError,
    NoPendingFollowUpGroupError,
    NoPendingToolCallSequenceError,
    PendingFollowUpQuestionsError,
    PendingToolCallsError,
    PlaylistTrackLimitExceededError,
    PlaylistTrackPinnedError,
    PlaylistTrackNotFoundError,
    PlaylistReferenceNotFoundError,
    SessionAccessDeniedError,
    UserCurationEventAlreadyConsumedError,
    UserCurationEventMissingTrackYearError,
    UserCurationEventNotFoundError,
)
from backend.features.session.domain import (
    AssistantMessage,
    CompletedCall,
    FailedCall,
    FollowUpOption,
    FollowUpQuestion,
    FollowUpQuestionGroup,
    FollowUpQuestionState,
    PendingCall,
    Phase,
    PlaylistTrack,
    Session,
    ToolCallSequence,
    ToolFunction,
    UserMessage,
    UserMessageAttachment,
    UserMessageAttachmentKind,
    UserCurationEvent,
    UserCurationEventType,
)


@pytest.fixture
def owner_id() -> UUID:
    return uuid4()


@pytest.fixture
def session(owner_id: UUID) -> Session:
    return Session(title="Roadtrip", entries=[], owner_id=owner_id)


def make_pending_call(call_id: str = "tc-1") -> PendingCall:
    return PendingCall(
        id=call_id,
        function=ToolFunction(name="search_track", arguments={"query": "daft punk"}),
    )


def make_pending_follow_up(question: str = "Welches Genre?") -> FollowUpQuestion:
    return FollowUpQuestion(
        question=question,
        options=[
            FollowUpOption(id="house", label="House"),
            FollowUpOption(id="techno", label="Techno"),
        ],
    )


class TestSessionDomainSession:
    def test_session_generates_aggregate_identity_by_default(
        self, owner_id: UUID
    ) -> None:
        created = Session(title="Roadtrip", entries=[], owner_id=owner_id)

        assert isinstance(created.id, UUID)
        assert created.created_at.tzinfo is not None
        assert created.created_at.utcoffset() == timezone.utc.utcoffset(None)

    def test_session_keeps_explicit_aggregate_identity(self, owner_id: UUID) -> None:
        session_id = uuid4()
        created_time = datetime(2026, 7, 7, tzinfo=timezone.utc)

        created = Session(
            title="Roadtrip",
            entries=[],
            owner_id=owner_id,
            id=session_id,
            created_time=created_time,
        )

        assert created.id == session_id
        assert created.created_at == created_time

    def test_create_with_initial_prompt_adds_first_user_message(
        self, owner_id: UUID
    ) -> None:
        created = Session.create_with_initial_prompt(
            title="Roadtrip",
            initial_prompt="spiele was ruhiges",
            owner_id=owner_id,
        )

        assert created.title == "Roadtrip"
        assert created.owner_id == owner_id
        assert len(created.entries) == 1
        assert isinstance(created.entries[0], UserMessage)
        assert created.entries[0].content == "spiele was ruhiges"

    def test_session_is_not_starred_by_default(self, owner_id: UUID) -> None:
        created = Session(title="Roadtrip", entries=[], owner_id=owner_id)

        assert created.is_starred is False

    def test_session_starts_in_build_phase(self, owner_id: UUID) -> None:
        created = Session(title="Roadtrip", entries=[], owner_id=owner_id)

        assert created.phase == Phase.BUILD

    def test_advance_to_building_phase_marks_onboarding_session_as_build(
        self, owner_id: UUID
    ) -> None:
        session = Session(
            title="Roadtrip",
            entries=[],
            owner_id=owner_id,
            phase=Phase.ONBOARDING,
        )

        session.advance_to_building_phase()

        assert session.phase == Phase.BUILD

    def test_advance_to_building_phase_rejects_non_onboarding_source(
        self, session: Session
    ) -> None:
        with pytest.raises(InvalidSessionPhaseTransitionError):
            session.advance_to_building_phase()

    def test_star_marks_session_as_starred(self, session: Session) -> None:
        session.star()

        assert session.is_starred is True

    def test_unstar_marks_session_as_not_starred(self, session: Session) -> None:
        session.star()

        session.unstar()

        assert session.is_starred is False

    def test_entries_property_is_immutable(self, session: Session) -> None:
        assert isinstance(session.entries, tuple)

        with pytest.raises(AttributeError, match="append"):
            session.entries.append(object())  # type: ignore[attr-defined]

    def test_add_user_message_appends_entry(self, session: Session) -> None:
        created = session.add_user_message("play something chill")

        assert len(session.entries) == 1
        assert session.entries[0] is created
        assert isinstance(created, UserMessage)

    def test_add_user_message_keeps_attachment_references(
        self, session: Session
    ) -> None:
        created = session.add_user_message(
            "nimm diese artist referenz",
            attachments=[
                UserMessageAttachment(
                    kind=UserMessageAttachmentKind.SPOTIFY_ARTIST,
                    external_id="1dfeR4HaWDbWqFHLkxsg1d",
                    title="Queen",
                    subtitle="Artist",
                    image_url="https://example.com/queen.jpg",
                    spotify_id="1dfeR4HaWDbWqFHLkxsg1d",
                )
            ],
        )

        assert len(created.attachments) == 1
        assert created.attachments[0].kind == UserMessageAttachmentKind.SPOTIFY_ARTIST
        assert created.attachments[0].title == "Queen"

    def test_add_user_message_raises_when_tool_calls_pending(
        self, session: Session
    ) -> None:
        session.add_tool_call(make_pending_call())

        with pytest.raises(PendingToolCallsError, match="tool calls are pending"):
            session.add_user_message("noch ein song")

    def test_add_user_message_raises_when_follow_up_questions_pending(
        self, session: Session
    ) -> None:
        session.add_follow_up_questions([make_pending_follow_up()])

        with pytest.raises(
            PendingFollowUpQuestionsError, match="follow-up questions are pending"
        ):
            session.add_user_message("antwort")

    def test_add_tool_call_auto_creates_sequence(self, session: Session) -> None:
        sequence = session.add_tool_call(make_pending_call("tc-1"))

        assert isinstance(sequence, ToolCallSequence)
        assert len(session.entries) == 1
        assert session.entries[0] is sequence
        assert len(sequence.calls) == 1

    def test_add_tool_call_appends_to_open_sequence(self, session: Session) -> None:
        first_sequence = session.add_tool_call(make_pending_call("tc-1"))
        second_sequence = session.add_tool_call(make_pending_call("tc-2"))

        assert first_sequence is second_sequence
        assert len(session.entries) == 1
        assert len(first_sequence.calls) == 2

    def test_add_tool_call_starts_new_sequence_after_assistant_message(
        self, session: Session
    ) -> None:
        session.add_user_message("recherche bitte")
        first_sequence = session.add_tool_call(make_pending_call("tc-1"))
        session.resolve_tool_call("tc-1", "ok")
        session.add_assistant_message("Zwischenergebnis")

        second_sequence = session.add_tool_call(make_pending_call("tc-2"))

        assert first_sequence is not second_sequence
        assert len(session.entries) == 4
        assert isinstance(session.entries[-1], ToolCallSequence)

    def test_add_tool_call_appends_to_completed_sequence(
        self, session: Session
    ) -> None:
        first_sequence = session.add_tool_call(make_pending_call("tc-1"))
        session.resolve_tool_call("tc-1", "ok")

        second_sequence = session.add_tool_call(make_pending_call("tc-2"))

        assert first_sequence is second_sequence
        assert len(session.entries) == 1
        assert first_sequence.calls[1].id == "tc-2"

    def test_add_assistant_message_creates_pure_text_entry(
        self, session: Session
    ) -> None:
        message = session.add_assistant_message(content="Hallo")

        assert isinstance(message, AssistantMessage)
        assert message.content == "Hallo"
        assert session.entries[-1] is message

    def test_append_to_current_assistant_message_updates_content(
        self, session: Session
    ) -> None:
        message = session.add_assistant_message(content="Hallo")

        updated = session.append_to_current_assistant_message(", Welt")

        assert updated is message
        assert updated.content == "Hallo, Welt"

    def test_append_to_current_assistant_message_raises_without_assistant(
        self, session: Session
    ) -> None:
        with pytest.raises(
            NoCurrentAssistantMessageError, match="no current assistant message"
        ):
            session.append_to_current_assistant_message("chunk")

    def test_cancel_current_assistant_message_removes_last_entry(
        self, session: Session
    ) -> None:
        removed = session.add_assistant_message(content="streaming...")

        cancelled = session.cancel_current_assistant_message()

        assert cancelled is removed
        assert len(session.entries) == 0

    def test_cancel_current_assistant_message_raises_without_assistant(
        self, session: Session
    ) -> None:
        with pytest.raises(
            NoCurrentAssistantMessageError, match="no current assistant message"
        ):
            session.cancel_current_assistant_message()

    def test_set_playlist_assigns_playlist(self, session: Session) -> None:
        playlist = session.set_playlist(tracks=[], name="Favorites")

        assert session.playlist is playlist
        assert session.playlist is not None
        assert session.playlist.name == "Favorites"

    def test_add_track_creates_playlist_if_missing(self, session: Session) -> None:
        track = session.add_track(title="Starlight", artist="Muse", year=2006)

        assert session.playlist is not None
        assert len(session.playlist.tracks) == 1
        assert session.playlist.tracks[0] is track

    def test_add_track_raises_when_playlist_track_limit_is_reached(
        self, session: Session
    ) -> None:
        for i in range(50):
            session.add_track(title=f"Track {i}", artist="Muse", year=2006)

        with pytest.raises(PlaylistTrackLimitExceededError, match="already has 50"):
            session.add_track(title="Overflow", artist="Muse", year=2006)

    def test_add_track_records_user_curation_event_snapshot(
        self, session: Session
    ) -> None:
        track = session.add_track(
            title="Starlight",
            artist="Muse",
            year=2006,
            spotify_uri="spotify:track:abc",
            cover_url="https://example.com/cover.jpg",
        )

        assert len(session.user_curation_events) == 1
        event = session.user_curation_events[0]
        assert event.event_type == UserCurationEventType.TRACK_ADDED
        assert event.track_id == track.id
        assert event.track_title == "Starlight"
        assert event.track_artist == "Muse"
        assert event.track_year == 2006
        assert event.track_spotify_uri == "spotify:track:abc"
        assert event.track_cover_url == "https://example.com/cover.jpg"
        assert event.consumed is False

    def test_add_user_message_binds_pending_user_curation_events(
        self, session: Session
    ) -> None:
        session.add_track(title="Starlight", artist="Muse", year=2006, is_pinned=False)

        message = session.add_user_message("weiter")

        assert len(message.user_curation_events) == 1
        assert (
            message.user_curation_events[0].event_type
            == UserCurationEventType.TRACK_ADDED
        )

    def test_constructor_does_not_hydrate_user_message_curation_events(
        self, owner_id: UUID
    ) -> None:
        message_time = datetime(2026, 7, 7, 12, 0, tzinfo=timezone.utc)
        message = UserMessage(content="weiter", created_time=message_time)
        event = UserCurationEvent(
            event_type=UserCurationEventType.TRACK_ADDED,
            track_id=uuid4(),
            track_title="Starlight",
            track_artist="Muse",
            track_year=2006,
            created_time=message_time,
        )

        Session(
            title="Roadtrip",
            entries=[message],
            owner_id=owner_id,
            user_curation_events=[event],
        )

        assert message.user_curation_events == ()

    def test_restore_user_curation_event_detaches_from_bound_user_message(
        self, session: Session
    ) -> None:
        session.add_track(title="Starlight", artist="Muse", year=2006, is_pinned=False)
        message = session.add_user_message("weiter")
        event = message.user_curation_events[0]

        session.restore_user_curation_event(event.id)

        assert message.user_curation_events == ()

    def test_remove_track_removes_matching_track(self, session: Session) -> None:
        first_track = session.add_track(title="Starlight", artist="Muse", year=2006)
        second_track = session.add_track(
            title="Teardrop", artist="Massive Attack", year=1998
        )

        session.remove_track(first_track.id)

        assert session.playlist is not None
        assert len(session.playlist.tracks) == 1
        assert session.playlist.tracks[0] is second_track

    def test_remove_track_records_user_curation_event_snapshot(
        self, session: Session
    ) -> None:
        track = session.add_track(
            title="Starlight",
            artist="Muse",
            year=2006,
            spotify_uri="spotify:track:abc",
            cover_url="https://example.com/cover.jpg",
        )

        session.remove_track(track.id)

        assert len(session.user_curation_events) == 2
        event = session.user_curation_events[1]
        assert event.event_type == UserCurationEventType.TRACK_REMOVED
        assert event.track_id == track.id
        assert event.track_title == "Starlight"
        assert event.track_artist == "Muse"
        assert event.track_spotify_uri == "spotify:track:abc"
        assert event.track_cover_url == "https://example.com/cover.jpg"

    def test_remove_track_raises_when_playlist_missing(self, session: Session) -> None:
        with pytest.raises(PlaylistTrackNotFoundError, match="has no playlist"):
            session.remove_track(uuid4())

    def test_remove_track_raises_when_track_missing(self, session: Session) -> None:
        session.add_track(title="Starlight", artist="Muse", year=2006)

        with pytest.raises(PlaylistTrackNotFoundError, match="not found in playlist"):
            session.remove_track(uuid4())

    def test_lock_and_unpin_track_updates_track_state(self, session: Session) -> None:
        track = session.add_track(title="Starlight", artist="Muse", year=2006)

        pinned = session.pin_track(track.id)
        unlocked = session.unpin_track(track.id)

        assert pinned is track
        assert unlocked is track
        assert track.is_pinned is False

    def test_pin_track_records_event_only_on_state_change(
        self, session: Session
    ) -> None:
        track = session.add_track(
            title="Starlight", artist="Muse", year=2006, is_pinned=False
        )

        session.pin_track(track.id)
        session.pin_track(track.id)

        event_types = [event.event_type for event in session.user_curation_events]
        assert event_types == [
            UserCurationEventType.TRACK_ADDED,
            UserCurationEventType.TRACK_PINNED,
        ]

    def test_unpin_track_records_event_only_on_state_change(
        self, session: Session
    ) -> None:
        track = session.add_track(
            title="Starlight", artist="Muse", year=2006, is_pinned=True
        )

        session.unpin_track(track.id)
        session.unpin_track(track.id)

        event_types = [event.event_type for event in session.user_curation_events]
        assert event_types == [
            UserCurationEventType.TRACK_ADDED,
            UserCurationEventType.TRACK_UNPINNED,
        ]

    def test_unconsumed_user_curation_events_filters_consumed(
        self, session: Session
    ) -> None:
        track = session.add_track(
            title="Starlight", artist="Muse", year=2006, is_pinned=False
        )
        session.pin_track(track.id)
        first_event = session.user_curation_events[0]
        first_event.mark_consumed()

        unconsumed = session.unconsumed_user_curation_events

        assert len(unconsumed) == 1
        assert unconsumed[0].event_type == UserCurationEventType.TRACK_PINNED

    def test_add_playlist_reference_appends_session_source(
        self, session: Session
    ) -> None:
        reference = session.add_playlist_reference(
            spotify_playlist_id="37i9dQZF1DX4dyzvuaRJ0n",
            name="Lo-Fi Beats",
            owner="Spotify",
            cover_url="https://example.com/cover.jpg",
            total_tracks=100,
        )

        assert session.playlist_references == (reference,)
        assert reference.spotify_playlist_id == "37i9dQZF1DX4dyzvuaRJ0n"
        assert reference.total_tracks == 100

    def test_add_playlist_reference_refreshes_existing_by_spotify_id(
        self, session: Session
    ) -> None:
        original = session.add_playlist_reference(
            spotify_playlist_id="37i9dQZF1DX4dyzvuaRJ0n",
            name="Old Name",
            owner="Old Owner",
        )

        updated = session.add_playlist_reference(
            spotify_playlist_id="37i9dQZF1DX4dyzvuaRJ0n",
            name="Lo-Fi Beats",
            owner="Spotify",
            cover_url="https://example.com/cover.jpg",
            total_tracks=100,
        )

        assert updated is original
        assert session.playlist_references == (original,)
        assert original.name == "Lo-Fi Beats"
        assert original.owner == "Spotify"
        assert original.cover_url == "https://example.com/cover.jpg"
        assert original.total_tracks == 100

    def test_remove_playlist_reference_removes_matching_reference(
        self, session: Session
    ) -> None:
        reference = session.add_playlist_reference(
            spotify_playlist_id="37i9dQZF1DX4dyzvuaRJ0n",
            name="Lo-Fi Beats",
        )

        session.remove_playlist_reference(reference.id)

        assert session.playlist_references == ()

    def test_remove_playlist_reference_raises_when_missing(
        self, session: Session
    ) -> None:
        with pytest.raises(PlaylistReferenceNotFoundError, match="not found"):
            session.remove_playlist_reference(uuid4())

    def test_add_artist_reference_refreshes_existing_by_spotify_id(
        self, session: Session
    ) -> None:
        original = session.add_artist_reference(
            spotify_artist_id="1dfeR4HaWDbWqFHLkxsg1d",
            name="Old Name",
        )

        updated = session.add_artist_reference(
            spotify_artist_id="1dfeR4HaWDbWqFHLkxsg1d",
            name="Queen",
            image_url="https://example.com/queen.jpg",
            genres=("rock", "glam rock"),
            followers=50_000_000,
            popularity=81,
        )

        assert updated is original
        assert session.artist_references == (original,)
        assert original.name == "Queen"
        assert original.image_url == "https://example.com/queen.jpg"
        assert original.genres == ("rock", "glam rock")
        assert original.followers == 50_000_000
        assert original.popularity == 81

    def test_remove_artist_reference_removes_matching_reference(
        self, session: Session
    ) -> None:
        reference = session.add_artist_reference(
            spotify_artist_id="1dfeR4HaWDbWqFHLkxsg1d",
            name="Queen",
        )

        session.remove_artist_reference(reference.id)

        assert session.artist_references == ()

    def test_remove_artist_reference_raises_when_missing(
        self, session: Session
    ) -> None:
        with pytest.raises(ArtistReferenceNotFoundError, match="not found"):
            session.remove_artist_reference(uuid4())

    def test_user_curation_event_snapshot_keeps_track_year(
        self, session: Session
    ) -> None:
        session.add_user_message("suche was mit synth")
        session.add_assistant_message("Hier sind ein paar Ideen")

        session.add_track(title="Starlight", artist="Muse", year=2006, is_pinned=False)

        assert len(session.user_curation_events) == 1
        assert session.user_curation_events[0].track_year == 2006

    def test_restore_user_curation_event_for_track_added_removes_track_and_event(
        self, session: Session
    ) -> None:
        track = session.add_track(
            title="Starlight", artist="Muse", year=2006, is_pinned=False
        )
        event = session.user_curation_events[0]

        session.restore_user_curation_event(event.id)

        assert session.user_curation_events == ()
        assert session.playlist is not None
        assert all(t.id != track.id for t in session.playlist.tracks)

    def test_restore_user_curation_event_for_track_removed_readds_track(
        self, session: Session
    ) -> None:
        track = session.add_track(
            title="Starlight",
            artist="Muse",
            year=2006,
            spotify_uri="spotify:track:abc",
            cover_url="https://example.com/cover.jpg",
            is_pinned=False,
        )
        session.remove_track(track.id)
        remove_event = session.user_curation_events[-1]

        session.restore_user_curation_event(remove_event.id)

        assert session.playlist is not None
        restored = session.playlist.tracks[-1]
        assert restored.id == track.id
        assert restored.title == "Starlight"
        assert restored.artist == "Muse"
        assert restored.year == 2006
        assert restored.spotify_uri == "spotify:track:abc"
        assert restored.cover_url == "https://example.com/cover.jpg"
        assert restored.is_pinned is False
        event_types = [event.event_type for event in session.user_curation_events]
        assert event_types == [UserCurationEventType.TRACK_ADDED]

    def test_restore_user_curation_event_for_track_removed_raises_when_year_missing(
        self, session: Session
    ) -> None:
        event = UserCurationEvent(
            event_type=UserCurationEventType.TRACK_REMOVED,
            track_id=uuid4(),
            track_title="Starlight",
            track_artist="Muse",
        )
        session = Session(
            title="Roadtrip",
            entries=[],
            owner_id=session.owner_id,
            user_curation_events=[event],
        )

        with pytest.raises(UserCurationEventMissingTrackYearError, match="track_year"):
            session.restore_user_curation_event(event.id)

    def test_restore_user_curation_event_for_track_pinned_unpins_track(
        self, session: Session
    ) -> None:
        track = session.add_track(
            title="Starlight", artist="Muse", year=2006, is_pinned=False
        )
        session.pin_track(track.id)
        pin_event = session.user_curation_events[-1]

        session.restore_user_curation_event(pin_event.id)

        assert track.is_pinned is False
        event_types = [event.event_type for event in session.user_curation_events]
        assert event_types == [UserCurationEventType.TRACK_ADDED]

    def test_restore_user_curation_event_for_track_unpinned_pins_track(
        self, session: Session
    ) -> None:
        track = session.add_track(
            title="Starlight", artist="Muse", year=2006, is_pinned=True
        )
        session.unpin_track(track.id)
        unpin_event = session.user_curation_events[-1]

        session.restore_user_curation_event(unpin_event.id)

        assert track.is_pinned is True
        event_types = [event.event_type for event in session.user_curation_events]
        assert event_types == [UserCurationEventType.TRACK_ADDED]

    def test_restore_user_curation_event_raises_when_event_missing(
        self, session: Session
    ) -> None:
        with pytest.raises(UserCurationEventNotFoundError, match="not found"):
            session.restore_user_curation_event(uuid4())

    def test_restore_user_curation_event_raises_when_event_already_consumed(
        self, session: Session
    ) -> None:
        session.add_track(title="Starlight", artist="Muse", year=2006, is_pinned=False)
        event = session.user_curation_events[0]
        event.mark_consumed()

        with pytest.raises(
            UserCurationEventAlreadyConsumedError, match="already been consumed"
        ):
            session.restore_user_curation_event(event.id)

    def test_restore_user_curation_event_for_pin_raises_when_track_was_removed(
        self, session: Session
    ) -> None:
        track = session.add_track(
            title="Starlight", artist="Muse", year=2006, is_pinned=False
        )
        session.pin_track(track.id)
        pin_event = session.user_curation_events[-1]
        session.remove_track(track.id)

        with pytest.raises(PlaylistTrackNotFoundError, match="not found"):
            session.restore_user_curation_event(pin_event.id)

    def test_replace_track_rejects_pinned_track(self, session: Session) -> None:
        track = session.add_track(
            title="Starlight",
            artist="Muse",
            year=2006,
            is_pinned=True,
        )

        with pytest.raises(PlaylistTrackPinnedError, match="pinned"):
            session.replace_track(
                track_id=track.id,
                track=PlaylistTrack(
                    title="Time Is Running Out", artist="Muse", year=2003
                ),
            )

    def test_set_playlist_preserves_pinned_tracks(self, session: Session) -> None:
        pinned_track = session.add_track(
            title="Starlight",
            artist="Muse",
            year=2006,
            is_pinned=True,
        )

        with pytest.raises(PlaylistTrackPinnedError, match="pinned"):
            session.set_playlist(
                tracks=[
                    PlaylistTrack(title="Teardrop", artist="Massive Attack", year=1998)
                ]
            )

        playlist = session.set_playlist(tracks=[pinned_track])

        assert playlist.tracks == [pinned_track]

    def test_resolve_tool_call_replaces_with_completed(self, session: Session) -> None:
        session.add_tool_call(make_pending_call("tc-1"))

        resolved = session.resolve_tool_call("tc-1", "done")

        assert isinstance(resolved, CompletedCall)
        assert resolved.result == "done"

    def test_fail_tool_call_replaces_with_failed(self, session: Session) -> None:
        session.add_tool_call(make_pending_call("tc-1"))

        failed = session.fail_tool_call("tc-1", "timeout")

        assert isinstance(failed, FailedCall)
        assert failed.error == "timeout"

    def test_remove_last_pending_tool_call_removes_empty_sequence(
        self, session: Session
    ) -> None:
        session.add_tool_call(make_pending_call("tc-1"))

        removed = session.remove_last_pending_tool_call()

        assert removed is not None
        assert removed.id == "tc-1"
        assert session.entries == ()

    def test_remove_last_pending_tool_call_keeps_resolved_calls(
        self, session: Session
    ) -> None:
        sequence = session.add_tool_call(make_pending_call("tc-1"))
        session.resolve_tool_call("tc-1", "ok")
        session.add_tool_call(make_pending_call("tc-2"))

        removed = session.remove_last_pending_tool_call()

        assert removed is not None
        assert removed.id == "tc-2"
        assert session.entries == (sequence,)
        assert [call.id for call in sequence.calls] == ["tc-1"]

    def test_resolve_tool_call_raises_without_pending_group(
        self, session: Session
    ) -> None:
        with pytest.raises(
            NoPendingToolCallSequenceError, match="no pending tool call sequence"
        ):
            session.resolve_tool_call("tc-1", "ok")

    def test_add_follow_up_questions_creates_group_entry(
        self, session: Session
    ) -> None:
        question = make_pending_follow_up()

        group = session.add_follow_up_questions([question])

        assert isinstance(group, FollowUpQuestionGroup)
        assert session.entries[-1] is group

    def test_answer_follow_up_with_option_resolves_question(
        self, session: Session
    ) -> None:
        question = make_pending_follow_up()
        session.add_follow_up_questions([question])

        answered = session.answer_follow_up_with_option(question.id, "house")

        assert answered is question
        assert answered.state == FollowUpQuestionState.ANSWERED
        assert answered.answer_text == "House"
        assert answered.answered_option_id == "house"

    def test_answer_follow_up_with_text_resolves_question(
        self, session: Session
    ) -> None:
        question = make_pending_follow_up()
        session.add_follow_up_questions([question])

        answered = session.answer_follow_up_with_text(question.id, "  chillwave  ")

        assert answered is question
        assert answered.state == FollowUpQuestionState.ANSWERED
        assert answered.answer_text == "chillwave"
        assert answered.answered_option_id is None

    def test_skip_follow_up_marks_question_skipped(self, session: Session) -> None:
        question = make_pending_follow_up()
        session.add_follow_up_questions([question])

        skipped = session.skip_follow_up(question.id)

        assert skipped is question
        assert skipped.state == FollowUpQuestionState.SKIPPED

    def test_skip_remaining_follow_ups_marks_only_pending_questions(
        self, session: Session
    ) -> None:
        first_question = make_pending_follow_up("Welches Genre?")
        second_question = make_pending_follow_up("Welche Stimmung?")
        third_question = make_pending_follow_up("Welches Tempo?")
        session.add_follow_up_questions(
            [first_question, second_question, third_question]
        )
        first_question.answer_with_text("house")

        skipped_questions = session.skip_remaining_follow_ups(
            question_id=second_question.id
        )

        assert skipped_questions == (second_question, third_question)
        assert first_question.state == FollowUpQuestionState.ANSWERED
        assert second_question.state == FollowUpQuestionState.SKIPPED
        assert third_question.state == FollowUpQuestionState.SKIPPED

    def test_answer_follow_up_raises_without_pending_group(
        self, session: Session
    ) -> None:
        with pytest.raises(
            NoPendingFollowUpGroupError, match="no pending follow-up question group"
        ):
            session.answer_follow_up_with_text(uuid4(), "anything")

    def test_has_access_allows_owner(self, session: Session, owner_id: UUID) -> None:
        session.has_access(owner_id)

    def test_has_access_raises_for_non_owner(self, session: Session) -> None:
        with pytest.raises(SessionAccessDeniedError, match="does not have access"):
            session.has_access(uuid4())
