from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest

from backend.features.session.domain.exceptions import (
    NoCurrentAssistantMessageError,
    NoPendingFollowUpGroupError,
    NoPendingToolCallSequenceError,
    PendingFollowUpQuestionsError,
    PendingToolCallsError,
    PlaylistTrackNotFoundError,
    SessionAccessDeniedError,
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
    Session,
    ToolCallSequence,
    ToolFunction,
    UserMessage,
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

    def test_remove_track_removes_matching_track(self, session: Session) -> None:
        first_track = session.add_track(title="Starlight", artist="Muse")
        second_track = session.add_track(title="Teardrop", artist="Massive Attack")

        session.remove_track(first_track.id)

        assert session.playlist is not None
        assert len(session.playlist.tracks) == 1
        assert session.playlist.tracks[0] is second_track

    def test_remove_track_raises_when_playlist_missing(self, session: Session) -> None:
        with pytest.raises(PlaylistTrackNotFoundError, match="has no playlist"):
            session.remove_track(uuid4())

    def test_remove_track_raises_when_track_missing(self, session: Session) -> None:
        session.add_track(title="Starlight", artist="Muse")

        with pytest.raises(PlaylistTrackNotFoundError, match="not found in playlist"):
            session.remove_track(uuid4())

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
