from datetime import datetime
from enum import StrEnum
from uuid import UUID

from backend.shared.ddd import Entity


class OnboardingQuestionSelectionMode(StrEnum):
    SINGLE_SELECT = "single_select"
    MULTI_SELECT = "multi_select"


class OnboardingQuestion(Entity):
    def __init__(
        self,
        *,
        sequence_number: int,
        question_text: str,
        options: tuple[str, ...] = (),
        selection_mode: OnboardingQuestionSelectionMode | str = (
            OnboardingQuestionSelectionMode.SINGLE_SELECT
        ),
        answers: tuple[str, ...] | None = None,
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
        self.selection_mode = OnboardingQuestionSelectionMode(selection_mode)
        self.answers = tuple(
            answers if answers is not None else ([answer] if answer else [])
        )
        self.is_last_question = is_last_question
        self.is_answered = is_answered
        self.answered_at = answered_at

    @property
    def allows_multiple_answers(self) -> bool:
        return self.selection_mode == OnboardingQuestionSelectionMode.MULTI_SELECT

    @property
    def answer(self) -> str | None:
        if not self.answers:
            return None
        return ", ".join(self.answers)

    def answer_with(self, answers: tuple[str, ...], *, answered_at: datetime) -> None:
        self.answers = answers
        self.is_answered = True
        self.answered_at = answered_at
