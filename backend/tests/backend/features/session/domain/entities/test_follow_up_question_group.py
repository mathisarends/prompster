from datetime import datetime, timezone
from uuid import uuid4

import pytest

from backend.features.session.domain import (
    FollowUpOption,
    FollowUpQuestion,
    FollowUpQuestionGroup,
    FollowUpQuestionNotFoundError,
)


def make_follow_up_question(label: str = "House") -> FollowUpQuestion:
    return FollowUpQuestion(
        question="Welches Genre?",
        options=[
            FollowUpOption(id="house", label=label),
            FollowUpOption(id="techno", label="Techno"),
        ],
    )


class TestSessionDomainFollowUpQuestionGroup:
    def test_group_keeps_explicit_entity_identity(self) -> None:
        group_id = uuid4()
        created_time = datetime(2026, 4, 4, tzinfo=timezone.utc)

        group = FollowUpQuestionGroup(
            questions=[make_follow_up_question()],
            id=group_id,
            created_time=created_time,
        )

        assert group.id == group_id
        assert group.created_at == created_time

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
