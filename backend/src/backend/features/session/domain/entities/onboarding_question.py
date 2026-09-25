from datetime import UTC, datetime
from enum import StrEnum
from typing import Self
from uuid import UUID, uuid4

from backend.shared.ddd import Entity


class OnboardingQuestionSelectionMode(StrEnum):
    SINGLE_SELECT = "single_select"
    MULTI_SELECT = "multi_select"


class OnboardingQuestion(Entity):
    def __init__(
        self,
        *,
        id: UUID,
        created_at: datetime,
        sequence_number: int,
        question_text: str,
        hint: str | None = None,
        options: tuple[str, ...] = (),
        recommended_option: str | None = None,
        selection_mode: OnboardingQuestionSelectionMode | str = (
            OnboardingQuestionSelectionMode.SINGLE_SELECT
        ),
        answers: tuple[str, ...] | None = None,
        is_last_question: bool = False,
        answer: str | None = None,
        is_answered: bool = False,
        answered_at: datetime | None = None,
    ) -> None:
        super().__init__(id=id, created_at=created_at)
        self.sequence_number = sequence_number
        self.question_text = question_text
        self.hint = hint
        self.options = tuple(options)
        self.recommended_option = recommended_option
        self.selection_mode = OnboardingQuestionSelectionMode(selection_mode)
        self.answers = tuple(
            answers if answers is not None else ([answer] if answer else [])
        )
        self.is_last_question = is_last_question
        self.is_answered = is_answered
        self.answered_at = answered_at

    @classmethod
    def create(
        cls,
        *,
        sequence_number: int,
        question_text: str,
        hint: str | None = None,
        options: tuple[str, ...] = (),
        recommended_option: str | None = None,
        selection_mode: OnboardingQuestionSelectionMode | str = (
            OnboardingQuestionSelectionMode.SINGLE_SELECT
        ),
        answers: tuple[str, ...] | None = None,
        is_last_question: bool = False,
        answer: str | None = None,
        is_answered: bool = False,
        answered_at: datetime | None = None,
    ) -> Self:
        return cls(
            id=uuid4(),
            created_at=datetime.now(UTC),
            sequence_number=sequence_number,
            question_text=question_text,
            hint=hint,
            options=options,
            recommended_option=recommended_option,
            selection_mode=selection_mode,
            answers=answers,
            is_last_question=is_last_question,
            answer=answer,
            is_answered=is_answered,
            answered_at=answered_at,
        )

    @classmethod
    def restore(
        cls,
        *,
        id: UUID,
        created_at: datetime,
        sequence_number: int,
        question_text: str,
        hint: str | None = None,
        options: tuple[str, ...] = (),
        recommended_option: str | None = None,
        selection_mode: OnboardingQuestionSelectionMode | str = (
            OnboardingQuestionSelectionMode.SINGLE_SELECT
        ),
        answers: tuple[str, ...] | None = None,
        is_last_question: bool = False,
        answer: str | None = None,
        is_answered: bool = False,
        answered_at: datetime | None = None,
    ) -> Self:
        return cls(
            id=id,
            created_at=created_at,
            sequence_number=sequence_number,
            question_text=question_text,
            hint=hint,
            options=options,
            recommended_option=recommended_option,
            selection_mode=selection_mode,
            answers=answers,
            is_last_question=is_last_question,
            answer=answer,
            is_answered=is_answered,
            answered_at=answered_at,
        )

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
