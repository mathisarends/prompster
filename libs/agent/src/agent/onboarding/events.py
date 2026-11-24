from dataclasses import dataclass, field
from enum import StrEnum
from typing import Literal

from harnessed.events import TransientEvent

from agent.onboarding.params import SelectionMode


class OnboardingEventKind(StrEnum):
    QUESTION_ASKED = "onboarding.question.asked"


@dataclass(frozen=True, slots=True)
class QuestionAskedEvent(TransientEvent):
    """A question for the user. The last one ends the turn until they answer."""

    question: str
    options: tuple[str, ...]
    hint: str | None = None
    recommended_option: str | None = None
    selection_mode: SelectionMode = SelectionMode.SINGLE_SELECT
    is_last_question: bool = False
    type: Literal[OnboardingEventKind.QUESTION_ASKED] = field(
        default=OnboardingEventKind.QUESTION_ASKED, kw_only=True
    )
