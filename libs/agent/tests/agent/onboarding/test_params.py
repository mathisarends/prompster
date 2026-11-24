import pytest
from agent.onboarding import SelectionMode
from agent.onboarding.params import AskOnboardingQuestionParams
from pydantic import ValidationError


@pytest.mark.parametrize("options", [["Solo"], [str(index) for index in range(5)]])
def test_question_rejects_option_counts_outside_range(options: list[str]) -> None:
    with pytest.raises(ValidationError, match="options"):
        AskOnboardingQuestionParams(question="Für wen?", options=options)


def test_question_defaults_to_single_select() -> None:
    params = AskOnboardingQuestionParams(question="Für wen?", options=["A", "B"])

    assert params.selection_mode is SelectionMode.SINGLE_SELECT
    assert params.is_last_question is False


def test_schema_keeps_hint_and_recommendation_optional() -> None:
    schema = AskOnboardingQuestionParams.model_json_schema()

    assert schema["properties"]["options"]["minItems"] == 2
    assert schema["properties"]["options"]["maxItems"] == 4
    assert "hint" not in schema["required"]
    assert "recommended_option" not in schema["required"]
