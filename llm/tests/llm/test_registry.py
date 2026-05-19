import pytest

from llm.registry import OPENAI_MODELS, OpenAIModelName, ensure_supported_openai_model


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
