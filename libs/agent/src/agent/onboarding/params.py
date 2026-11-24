from enum import StrEnum

from pydantic import BaseModel, Field


class SelectionMode(StrEnum):
    SINGLE_SELECT = "single_select"
    MULTI_SELECT = "multi_select"


class AskOnboardingQuestionParams(BaseModel):
    question: str = Field(description="The question shown to the user.")
    hint: str | None = Field(
        default=None,
        description="Optional short note below the question: a tip or a warning.",
    )
    selection_mode: SelectionMode = Field(
        default=SelectionMode.SINGLE_SELECT,
        description="single_select for one answer, multi_select for several.",
    )
    options: list[str] = Field(
        min_length=2,
        max_length=4,
        description="2-4 tag-style answers of about three words each.",
    )
    recommended_option: str | None = Field(
        default=None,
        description="Your recommendation, copied verbatim from options.",
    )
    is_last_question: bool = Field(
        default=False,
        description="True only on the final question of this onboarding.",
    )
