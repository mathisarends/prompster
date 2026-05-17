from datetime import datetime, timezone
from uuid import uuid4

import pytest

from backend.features.session.domain import (
    EmptyFollowUpAnswerError,
    FollowUpOption,
    FollowUpOptionNotFoundError,
    FollowUpQuestion,
    FollowUpQuestionAlreadyResolvedError,
    FollowUpQuestionState,
)


def make_follow_up_question(label: str = "House") -> FollowUpQuestion:
    return FollowUpQuestion(
        question="Welches Genre?",
        options=[
            FollowUpOption(id="house", label=label),
            FollowUpOption(id="techno", label="Techno"),
        ],
    )


class TestSessionDomainFollowUpQuestion:
    def test_follow_up_question_keeps_explicit_entity_identity(self) -> None:
        question_id = uuid4()
        created_time = datetime(2026, 3, 3, tzinfo=timezone.utc)

        question = FollowUpQuestion(
            question="Welches Genre?",
            options=[FollowUpOption(id="house", label="House")],
            id=question_id,
            created_time=created_time,
        )

        assert question.id == question_id
        assert question.created_at == created_time

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
