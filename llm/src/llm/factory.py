from llmify import ChatOpenAI

from llm.registry import (
    DEFAULT_OPENAI_MODEL,
    ModelId,
    ensure_supported_openai_model,
)
from llm.credentials import LLMCredentials


def _resolve_openai_api_key(
    api_key: str | None,
    credentials: LLMCredentials | None,
) -> str:
    if api_key is not None:
        return api_key
    active_credentials = credentials or LLMCredentials()
    return active_credentials.openai_api_key


def create_openai_llm(
    model: ModelId = DEFAULT_OPENAI_MODEL,
    *,
    api_key: str | None = None,
    credentials: LLMCredentials | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    **kwargs: object,
) -> ChatOpenAI:
    selected_model = ensure_supported_openai_model(model)
    resolved_api_key = _resolve_openai_api_key(api_key, credentials)
    options: dict[str, object] = {
        "model": selected_model,
        "api_key": resolved_api_key,
    }

    if temperature is not None:
        options["temperature"] = temperature
    if max_tokens is not None:
        options["max_tokens"] = max_tokens

    return ChatOpenAI(**kwargs, **options)


def create_gpt_5_4(
    *,
    api_key: str | None = None,
    credentials: LLMCredentials | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    **kwargs: object,
) -> ChatOpenAI:
    return create_openai_llm(
        model=ModelId.GPT_5_4,
        api_key=api_key,
        credentials=credentials,
        temperature=temperature,
        max_tokens=max_tokens,
        **kwargs,
    )


def create_gpt_5_4_mini(
    *,
    api_key: str | None = None,
    credentials: LLMCredentials | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    **kwargs: object,
) -> ChatOpenAI:
    return create_openai_llm(
        model=ModelId.GPT_5_4_MINI,
        api_key=api_key,
        credentials=credentials,
        temperature=temperature,
        max_tokens=max_tokens,
        **kwargs,
    )


def create_gpt_5_5(
    *,
    api_key: str | None = None,
    credentials: LLMCredentials | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    **kwargs: object,
) -> ChatOpenAI:
    return create_openai_llm(
        model=ModelId.GPT_5_5,
        api_key=api_key,
        credentials=credentials,
        temperature=temperature,
        max_tokens=max_tokens,
        **kwargs,
    )
