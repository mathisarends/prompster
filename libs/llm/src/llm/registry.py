from dataclasses import dataclass
from enum import StrEnum
from typing import Final, TypeGuard


class LLMProvider(StrEnum):
    OPENAI = "openai"


@dataclass(frozen=True)
class LLMModelInfo:
    id: str
    display_name: str
    provider: LLMProvider
    input_token_limit: int


class ModelId(StrEnum):
    GPT_5_4 = "gpt-5.4"
    GPT_5_4_MINI = "gpt-5.4-mini"
    GPT_5_5 = "gpt-5.5"


OPENAI_MODEL_REGISTRY: Final[dict[ModelId, LLMModelInfo]] = {
    ModelId.GPT_5_4: LLMModelInfo(
        id=ModelId.GPT_5_4,
        display_name="GPT-5.4",
        provider=LLMProvider.OPENAI,
        input_token_limit=272_000,
    ),
    ModelId.GPT_5_4_MINI: LLMModelInfo(
        id=ModelId.GPT_5_4_MINI,
        display_name="GPT-5.4 Mini",
        provider=LLMProvider.OPENAI,
        input_token_limit=272_000,
    ),
    ModelId.GPT_5_5: LLMModelInfo(
        id=ModelId.GPT_5_5,
        display_name="GPT-5.5",
        provider=LLMProvider.OPENAI,
        input_token_limit=272_000,
    ),
}

OPENAI_MODELS: Final[tuple[ModelId, ...]] = tuple(OPENAI_MODEL_REGISTRY.keys())
DEFAULT_OPENAI_MODEL: Final[ModelId] = ModelId.GPT_5_4_MINI


def _is_supported_openai_model(model: str) -> TypeGuard[ModelId]:
    return any(model == m.value for m in OPENAI_MODELS)


def ensure_supported_openai_model(model: str) -> ModelId:
    if _is_supported_openai_model(model):
        return ModelId(model)
    supported_models = ", ".join(m.value for m in OPENAI_MODELS)
    msg = f"Unsupported OpenAI model '{model}'. Supported models: {supported_models}."
    raise ValueError(msg)


def get_model_info(model: str | ModelId) -> LLMModelInfo:
    selected = ensure_supported_openai_model(model)
    return OPENAI_MODEL_REGISTRY[selected]


def get_openai_model_input_token_limit(model: str | ModelId) -> int:
    return get_model_info(model).input_token_limit
