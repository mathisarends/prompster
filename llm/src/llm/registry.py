from enum import StrEnum
from typing import Final, TypeGuard


class LLMProvider(StrEnum):
    OPENAI = "openai"


class OpenAIModelName(StrEnum):
    GPT_5_4 = "gpt-5.4"
    GPT_5_4_MINI = "gpt-5.4-mini"
    GPT_5_5 = "gpt-5.5"


OPENAI_MODELS: Final[tuple[OpenAIModelName, ...]] = (
    OpenAIModelName.GPT_5_4,
    OpenAIModelName.GPT_5_4_MINI,
    OpenAIModelName.GPT_5_5,
)

DEFAULT_OPENAI_MODEL: Final[OpenAIModelName] = OpenAIModelName.GPT_5_4_MINI

OPENAI_MODEL_INPUT_TOKEN_LIMITS: Final[dict[OpenAIModelName, int]] = {
    OpenAIModelName.GPT_5_4: 272_000,
    OpenAIModelName.GPT_5_4_MINI: 272_000,
    OpenAIModelName.GPT_5_5: 272_000,
}


def _is_supported_openai_model(model: str) -> TypeGuard[OpenAIModelName]:
    return any(model == m.value for m in OPENAI_MODELS)


def ensure_supported_openai_model(model: str) -> OpenAIModelName:
    if _is_supported_openai_model(model):
        return OpenAIModelName(model)
    supported_models = ", ".join(m.value for m in OPENAI_MODELS)
    msg = f"Unsupported OpenAI model '{model}'. Supported models: {supported_models}."
    raise ValueError(msg)


def get_openai_model_input_token_limit(model: str | OpenAIModelName) -> int:
    selected_model = ensure_supported_openai_model(model)
    return OPENAI_MODEL_INPUT_TOKEN_LIMITS[selected_model]
