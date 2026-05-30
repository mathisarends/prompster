from datetime import datetime
from uuid import UUID

from backend.shared.ddd import Entity


class OnboardingQuestion(Entity):
    def __init__(
        self,
        *,
        sequence_number: int,
        question_text: str,
        options: tuple[str, ...] = (),
        is_last_question: bool = False,
        answer: str | None = None,
        is_answered: bool = False,
        answered_at: datetime | None = None,
        id: UUID | None = None,
        created_time: datetime | None = None,
    ) -> None:
        super().__init__(id=id, created_time=created_time)
        self.sequence_number = sequence_number
        self.question_text = question_text
        self.options = tuple(options)
        self.is_last_question = is_last_question
        self.answer = answer
        self.is_answered = is_answered
        self.answered_at = answered_at

    def answer_with(self, answer: str, *, answered_at: datetime) -> None:
        self.answer = answer
        self.is_answered = True
        self.answered_at = answered_at
