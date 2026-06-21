import pytest

from llm.registry import (
    OPENAI_MODELS,
    OpenAIModelName,
    ensure_supported_openai_model,
    get_openai_model_input_token_limit,
)


class TestRegistry:
    @pytest.mark.parametrize("model", OPENAI_MODELS)
    def test_ensure_supported_openai_model_accepts_enum_values(
        self, model: OpenAIModelName
    ) -> None:
        assert ensure_supported_openai_model(model) == model

    @pytest.mark.parametrize("model", OPENAI_MODELS)
    def test_ensure_supported_openai_model_accepts_raw_string_values(
        self, model: OpenAIModelName
    ) -> None:
        assert ensure_supported_openai_model(model.value) == model

    def test_ensure_supported_openai_model_raises_for_unknown_model(self) -> None:
        with pytest.raises(ValueError, match="Unsupported OpenAI model"):
            ensure_supported_openai_model("gpt-4.1")

    @pytest.mark.parametrize("model", OPENAI_MODELS)
    def test_get_openai_model_input_token_limit_returns_positive_limit(
        self, model: OpenAIModelName
    ) -> None:
        assert get_openai_model_input_token_limit(model) > 0

    def test_get_openai_model_input_token_limit_accepts_raw_string(self) -> None:
        assert get_openai_model_input_token_limit("gpt-5.4-mini") == 272_000
