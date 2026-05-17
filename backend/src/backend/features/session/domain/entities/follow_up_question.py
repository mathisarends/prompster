from datetime import datetime
from enum import StrEnum
from uuid import UUID

from backend.features.session.domain.exceptions import (
    EmptyFollowUpAnswerError,
    FollowUpOptionNotFoundError,
    FollowUpQuestionAlreadyResolvedError,
)
from backend.shared.ddd import Entity


class FollowUpQuestionState(StrEnum):
    PENDING = "pending"
    ANSWERED = "answered"
    SKIPPED = "skipped"


class FollowUpOption:
    def __init__(self, id: str, label: str) -> None:
        self.id = id
        self.label = label


class FollowUpQuestion(Entity):
    def __init__(
        self,
        question: str,
        options: list[FollowUpOption],
        state: FollowUpQuestionState = FollowUpQuestionState.PENDING,
        answer_text: str | None = None,
        answered_option_id: str | None = None,
        id: UUID | None = None,
        created_time: datetime | None = None,
    ) -> None:
        super().__init__(id=id, created_time=created_time)
        self.question = question
        self.options = options
        self.state = state
        self.answer_text = answer_text
        self.answered_option_id = answered_option_id

    @property
    def is_pending(self) -> bool:
        return self.state == FollowUpQuestionState.PENDING

    @property
    def is_resolved(self) -> bool:
        return self.state != FollowUpQuestionState.PENDING

    def answer_with_option(self, option_id: str) -> FollowUpOption:
        self._assert_pending()
        option = self._find_option(option_id)
        self.state = FollowUpQuestionState.ANSWERED
        self.answer_text = option.label
        self.answered_option_id = option.id
        return option

    def answer_with_text(self, text: str) -> None:
        self._assert_pending()
        cleaned = text.strip()
        if not cleaned:
            raise EmptyFollowUpAnswerError(
                f"Free-text answer for question {self.id} must not be empty."
            )
        self.state = FollowUpQuestionState.ANSWERED
        self.answer_text = cleaned
        self.answered_option_id = None

    def skip(self) -> None:
        self._assert_pending()
        self.state = FollowUpQuestionState.SKIPPED

    def _assert_pending(self) -> None:
        if self.is_resolved:
            raise FollowUpQuestionAlreadyResolvedError(
                f"Follow-up question {self.id} is already {self.state}."
            )

    def _find_option(self, option_id: str) -> FollowUpOption:
        for option in self.options:
            if option.id == option_id:
                return option
        raise FollowUpOptionNotFoundError(
            f"No option {option_id!r} on follow-up question {self.id}."
        )
