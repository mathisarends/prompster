from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest

from backend.features.session.domain import (
    EmptyFollowUpAnswerError,
    FollowUpOption,
    FollowUpOptionNotFoundError,
    FollowUpQuestion,
    FollowUpQuestionAlreadyResolvedError,
    FollowUpQuestionGroup,
    FollowUpQuestionNotFoundError,
    FollowUpQuestionState,
    MessageRole,
    Playlist,
    PlaylistTrack,
    SessionMessage,
    ToolCall,
    ToolCallGroup,
    ToolCallState,
    ToolFunction,
)


def make_follow_up_question(label: str = "House") -> FollowUpQuestion:
    return FollowUpQuestion(
        question="Welches Genre?",
        options=[
            FollowUpOption(id="house", label=label),
            FollowUpOption(id="techno", label="Techno"),
        ],
    )


def make_tool_call(call_id: str = "tc-1") -> ToolCall:
    return ToolCall(
        id=call_id,
        function=ToolFunction(name="search_track", arguments={"query": "electro"}),
    )


class TestSessionDomainPlaylistEntities:
    def test_playlist_track_assigns_constructor_fields(self) -> None:
        track_id: UUID = uuid4()
        created_time = datetime(2026, 1, 1, tzinfo=timezone.utc)

        track = PlaylistTrack(
            id=track_id,
            title="Starlight",
            artist="Muse",
            year=2006,
            cover_url="https://example.com/starlight.jpg",
            created_time=created_time,
        )

        assert track.id == track_id
        assert track.created_at == created_time
        assert track.title == "Starlight"
        assert track.artist == "Muse"
        assert track.year == 2006
        assert track.cover_url == "https://example.com/starlight.jpg"

    def test_playlist_assigns_tracks_and_name(self) -> None:
        track = PlaylistTrack(title="Teardrop", artist="Massive Attack")

        playlist = Playlist(tracks=[track], name="Favorites")

        assert playlist.name == "Favorites"
        assert playlist.tracks == [track]


class TestSessionDomainFollowUpQuestion:
    def test_answer_with_option_sets_state_and_answer_fields(self) -> None:
        question = make_follow_up_question(label="House")

        chosen = question.answer_with_option("house")

        assert chosen.id == "house"
        assert question.state == FollowUpQuestionState.ANSWERED
        assert question.answer_text == "House"
        assert question.answered_option_id == "house"

    def test_answer_with_option_raises_when_option_missing(self) -> None:
        question = make_follow_up_question()

        with pytest.raises(FollowUpOptionNotFoundError, match="No option"):
            question.answer_with_option("drum-and-bass")

    def test_answer_with_text_trims_input(self) -> None:
        question = make_follow_up_question()

        question.answer_with_text("  melodic techno  ")

        assert question.state == FollowUpQuestionState.ANSWERED
        assert question.answer_text == "melodic techno"
        assert question.answered_option_id is None

    def test_answer_with_text_raises_when_blank(self) -> None:
        question = make_follow_up_question()

        with pytest.raises(EmptyFollowUpAnswerError, match="must not be empty"):
            question.answer_with_text("   ")

    def test_skip_sets_state_to_skipped(self) -> None:
        question = make_follow_up_question()

        question.skip()

        assert question.state == FollowUpQuestionState.SKIPPED

    def test_skip_raises_when_question_is_already_resolved(self) -> None:
        question = make_follow_up_question()
        question.answer_with_text("house")

        with pytest.raises(FollowUpQuestionAlreadyResolvedError, match="already"):
            question.skip()


class TestSessionDomainFollowUpQuestionGroup:
    def test_pending_questions_and_current_question_follow_pending_order(self) -> None:
        first_question = make_follow_up_question(label="House")
        second_question = make_follow_up_question(label="Tech House")
        group = FollowUpQuestionGroup(questions=[first_question, second_question])

        first_question.answer_with_text("done")

        assert len(group.pending_questions) == 1
        assert group.pending_questions[0] is second_question
        assert group.current_question is second_question

    def test_is_complete_is_true_when_all_questions_are_resolved(self) -> None:
        first_question = make_follow_up_question(label="House")
        second_question = make_follow_up_question(label="Tech House")
        group = FollowUpQuestionGroup(questions=[first_question, second_question])

        first_question.answer_with_text("done")
        second_question.skip()

        assert group.is_complete is True
        assert group.current_question is None

    def test_answer_with_option_updates_matching_question(self) -> None:
        question = make_follow_up_question()
        group = FollowUpQuestionGroup(questions=[question])

        updated = group.answer_with_option(question.id, "techno")

        assert updated is question
        assert updated.answer_text == "Techno"
        assert updated.answered_option_id == "techno"

    def test_answer_with_text_raises_for_unknown_question(self) -> None:
        group = FollowUpQuestionGroup(questions=[make_follow_up_question()])

        with pytest.raises(
            FollowUpQuestionNotFoundError, match="No follow-up question"
        ):
            group.answer_with_text(uuid4(), "unknown")

    def test_skip_raises_for_unknown_question(self) -> None:
        group = FollowUpQuestionGroup(questions=[make_follow_up_question()])

        with pytest.raises(
            FollowUpQuestionNotFoundError, match="No follow-up question"
        ):
            group.skip(uuid4())


class TestSessionDomainToolCallGroup:
    def test_fail_marks_matching_tool_call_as_failed(self) -> None:
        call = make_tool_call()
        group = ToolCallGroup(calls=[call])

        failed = group.fail("tc-1", "timeout")

        assert failed is call
        assert failed.state == ToolCallState.FAILED
        assert failed.error == "timeout"

    def test_is_complete_is_true_when_all_calls_are_resolved(self) -> None:
        first_call = make_tool_call(call_id="tc-1")
        second_call = make_tool_call(call_id="tc-2")
        group = ToolCallGroup(calls=[first_call, second_call])

        first_call.complete("ok")
        second_call.fail("timeout")

        assert group.is_complete is True


class TestSessionDomainSessionMessage:
    def test_session_message_keeps_role_content_and_groups(self) -> None:
        tool_call_group = ToolCallGroup(calls=[make_tool_call()])
        follow_up_group = FollowUpQuestionGroup(questions=[make_follow_up_question()])

        message = SessionMessage(
            role=MessageRole.ASSISTANT,
            content="Noch eine Frage",
            tool_call_group=tool_call_group,
            follow_up_group=follow_up_group,
        )

        assert message.role == MessageRole.ASSISTANT
        assert message.content == "Noch eine Frage"
        assert message.tool_call_group is tool_call_group
        assert message.follow_up_group is follow_up_group
