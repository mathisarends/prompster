from llmify import ChatModel, ChatOpenAIResponses

from backend.features.llm.application import ChatModelFactory
from backend.features.llm.domain import LLMModelInfo
from backend.features.llm.infrastructure.credentials import LLMCredentials


def _resolve_openai_api_key(
    api_key: str | None,
    credentials: LLMCredentials | None,
) -> str:
    if api_key is not None:
        return api_key
    active_credentials = credentials or LLMCredentials()
    return active_credentials.openai_api_key


def create_openai_llm(
    provider_model: str,
    *,
    api_key: str | None = None,
    credentials: LLMCredentials | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    **kwargs: object,
) -> ChatOpenAIResponses:
    """Create a client; available application models are owned by LLMRegistry."""
    options: dict[str, object] = {
        "model": provider_model,
        "api_key": _resolve_openai_api_key(api_key, credentials),
    }
    if temperature is not None:
        options["temperature"] = temperature
    if max_tokens is not None:
        options["max_tokens"] = max_tokens
    return ChatOpenAIResponses(**kwargs, **options)


class OpenAIChatModelFactory(ChatModelFactory):
    def __init__(self, credentials: LLMCredentials) -> None:
        self._credentials = credentials

    def create(self, model: LLMModelInfo) -> ChatModel:
        return create_openai_llm(
            provider_model=model.provider_model,
            credentials=self._credentials,
        )
