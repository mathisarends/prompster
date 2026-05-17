from datetime import datetime
from uuid import UUID

from backend.features.session.domain.entities.follow_up_question import (
    FollowUpQuestion,
)
from backend.features.session.domain.exceptions import (
    FollowUpQuestionNotFoundError,
)
from backend.shared.ddd import Entity


class FollowUpQuestionGroup(Entity):
    def __init__(
        self,
        questions: list[FollowUpQuestion],
        id: UUID | None = None,
        created_time: datetime | None = None,
    ) -> None:
        super().__init__(id=id, created_time=created_time)
        self.questions = questions

    @property
    def is_complete(self) -> bool:
        return all(question.is_resolved for question in self.questions)

    @property
    def pending_questions(self) -> list[FollowUpQuestion]:
        return [question for question in self.questions if question.is_pending]

    @property
    def current_question(self) -> FollowUpQuestion | None:
        for question in self.questions:
            if question.is_pending:
                return question
        return None

    def answer_with_option(self, question_id: UUID, option_id: str) -> FollowUpQuestion:
        question = self._get(question_id)
        question.answer_with_option(option_id)
        return question

    def answer_with_text(self, question_id: UUID, text: str) -> FollowUpQuestion:
        question = self._get(question_id)
        question.answer_with_text(text)
        return question

    def skip(self, question_id: UUID) -> FollowUpQuestion:
        question = self._get(question_id)
        question.skip()
        return question

    def _get(self, question_id: UUID) -> FollowUpQuestion:
        for question in self.questions:
            if question.id == question_id:
                return question
        raise FollowUpQuestionNotFoundError(
            f"No follow-up question {question_id} in group {self.id}."
        )
