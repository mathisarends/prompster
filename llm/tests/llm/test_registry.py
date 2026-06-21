import pytest

from llm.registry import (
    LLMModelInfo,
    OPENAI_MODEL_REGISTRY,
    OPENAI_MODELS,
    ModelId,
    ensure_supported_openai_model,
    get_model_info,
    get_openai_model_input_token_limit,
)


class TestRegistry:
    @pytest.mark.parametrize("model", OPENAI_MODELS)
    def test_ensure_supported_openai_model_accepts_enum_values(
        self, model: ModelId
    ) -> None:
        assert ensure_supported_openai_model(model) == model

    @pytest.mark.parametrize("model", OPENAI_MODELS)
    def test_ensure_supported_openai_model_accepts_raw_string_values(
        self, model: ModelId
    ) -> None:
        assert ensure_supported_openai_model(model.value) == model

    def test_ensure_supported_openai_model_raises_for_unknown_model(self) -> None:
        with pytest.raises(ValueError, match="Unsupported OpenAI model"):
            ensure_supported_openai_model("gpt-4.1")

    @pytest.mark.parametrize("model", OPENAI_MODELS)
    def test_get_openai_model_input_token_limit_returns_positive_limit(
        self, model: ModelId
    ) -> None:
        assert get_openai_model_input_token_limit(model) > 0

    def test_get_openai_model_input_token_limit_accepts_raw_string(self) -> None:
        assert get_openai_model_input_token_limit("gpt-5.4-mini") == 272_000

    @pytest.mark.parametrize("model", OPENAI_MODELS)
    def test_get_model_info_returns_llm_model_info(self, model: ModelId) -> None:
        info = get_model_info(model)
        assert isinstance(info, LLMModelInfo)

    @pytest.mark.parametrize("model", OPENAI_MODELS)
    def test_get_model_info_id_matches_model_name(self, model: ModelId) -> None:
        assert get_model_info(model).id == model.value

    @pytest.mark.parametrize("model", OPENAI_MODELS)
    def test_get_model_info_input_token_limit_is_positive(self, model: ModelId) -> None:
        assert get_model_info(model).input_token_limit > 0

    @pytest.mark.parametrize("model", OPENAI_MODELS)
    def test_registry_contains_all_models(self, model: ModelId) -> None:
        assert model in OPENAI_MODEL_REGISTRY

    def test_get_model_info_raises_for_unknown_model(self) -> None:
        with pytest.raises(ValueError, match="Unsupported OpenAI model"):
            get_model_info("gpt-4.1")
