from uuid import UUID, uuid4

import pytest

from backend.features.session.domain.exceptions import (
    NoCurrentAssistantMessageError,
    NoPendingFollowUpGroupError,
    NoPendingToolCallGroupError,
    PendingFollowUpQuestionsError,
    PendingToolCallsError,
    PlaylistTrackNotFoundError,
    SessionAccessDeniedError,
)
from backend.features.session.domain import (
    FollowUpOption,
    FollowUpQuestion,
    FollowUpQuestionState,
    MessageRole,
    Session,
    ToolCall,
    ToolCallState,
    ToolFunction,
)


@pytest.fixture
def owner_id() -> UUID:
    return uuid4()


@pytest.fixture
def session(owner_id: UUID) -> Session:
    return Session(title="Roadtrip", messages=[], owner_id=owner_id)


def make_pending_tool_call(call_id: str = "tc-1") -> ToolCall:
    return ToolCall(
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
        assert len(created.messages) == 1
        assert created.messages[0].role == MessageRole.USER
        assert created.messages[0].content == "spiele was ruhiges"

    def test_messages_property_is_immutable(self, session: Session) -> None:
        assert isinstance(session.messages, tuple)

        with pytest.raises(AttributeError, match="append"):
            session.messages.append(object())

    def test_add_user_message_appends_internal_messages(self, session: Session) -> None:
        created = session.add_user_message("play something chill")

        assert len(session.messages) == 1
        assert session.messages[0] is created

    def test_add_user_message_raises_when_tool_calls_pending(
        self, session: Session
    ) -> None:
        pending_call = make_pending_tool_call()
        session.add_assistant_message(
            content="Ich suche Tracks...", tool_calls=[pending_call]
        )

        with pytest.raises(PendingToolCallsError, match="tool calls are pending"):
            session.add_user_message("noch ein song")

    def test_add_user_message_raises_when_follow_up_questions_pending(
        self, session: Session
    ) -> None:
        session.add_assistant_message(
            content="Noch eine Frage...",
            follow_up_questions=[make_pending_follow_up()],
        )

        with pytest.raises(
            PendingFollowUpQuestionsError, match="follow-up questions are pending"
        ):
            session.add_user_message("antwort")

    def test_add_assistant_message_attaches_pending_groups(
        self, session: Session
    ) -> None:
        tool_call = make_pending_tool_call()
        follow_up = make_pending_follow_up()

        message = session.add_assistant_message(
            content="Ich brauche noch Infos",
            tool_calls=[tool_call],
            follow_up_questions=[follow_up],
        )

        assert message.role == MessageRole.ASSISTANT
        assert message.tool_call_group is not None
        assert message.follow_up_group is not None
        assert message.tool_call_group.calls[0] is tool_call
        assert message.follow_up_group.questions[0] is follow_up

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

    def test_cancel_current_assistant_message_removes_last_message(
        self, session: Session
    ) -> None:
        removed = session.add_assistant_message(content="streaming...")

        cancelled = session.cancel_current_assistant_message()

        assert cancelled is removed
        assert len(session.messages) == 0

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

    def test_resolve_tool_call_marks_call_completed(self, session: Session) -> None:
        pending_call = make_pending_tool_call(call_id="tc-1")
        session.add_assistant_message(tool_calls=[pending_call])

        resolved = session.resolve_tool_call("tc-1", "done")

        assert resolved.state == ToolCallState.COMPLETED
        assert resolved.result == "done"

    def test_fail_tool_call_marks_call_failed(self, session: Session) -> None:
        pending_call = make_pending_tool_call(call_id="tc-1")
        session.add_assistant_message(tool_calls=[pending_call])

        failed = session.fail_tool_call("tc-1", "timeout")

        assert failed.state == ToolCallState.FAILED
        assert failed.error == "timeout"

    def test_resolve_tool_call_raises_without_pending_group(
        self, session: Session
    ) -> None:
        with pytest.raises(
            NoPendingToolCallGroupError, match="no pending tool call group"
        ):
            session.resolve_tool_call("tc-1", "ok")

    def test_answer_follow_up_with_option_resolves_question(
        self, session: Session
    ) -> None:
        question = make_pending_follow_up()
        session.add_assistant_message(follow_up_questions=[question])

        answered = session.answer_follow_up_with_option(question.id, "house")

        assert answered is question
        assert answered.state == FollowUpQuestionState.ANSWERED
        assert answered.answer_text == "House"
        assert answered.answered_option_id == "house"

    def test_answer_follow_up_with_text_resolves_question(
        self, session: Session
    ) -> None:
        question = make_pending_follow_up()
        session.add_assistant_message(follow_up_questions=[question])

        answered = session.answer_follow_up_with_text(question.id, "  chillwave  ")

        assert answered is question
        assert answered.state == FollowUpQuestionState.ANSWERED
        assert answered.answer_text == "chillwave"
        assert answered.answered_option_id is None

    def test_skip_follow_up_marks_question_skipped(self, session: Session) -> None:
        question = make_pending_follow_up()
        session.add_assistant_message(follow_up_questions=[question])

        skipped = session.skip_follow_up(question.id)

        assert skipped is question
        assert skipped.state == FollowUpQuestionState.SKIPPED

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
