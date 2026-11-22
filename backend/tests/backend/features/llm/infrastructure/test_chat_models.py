import asyncio
import json

import httpx2
import pytest
from openai import AsyncOpenAI
from pydantic_ai.direct import model_request_stream
from pydantic_ai.exceptions import ModelHTTPError
from pydantic_ai.messages import ModelRequest, SystemPromptPart, UserPromptPart
from pydantic_ai.models.openai import OpenAIResponsesModel
from pydantic_ai.models.openai_codex import OpenAICodexModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.providers.openai_codex import OpenAICodexProvider

from backend.features.llm.domain import (
    LLMModelInfo,
    LLMProvider,
    ModelCapabilities,
    ModelDefaults,
    ModelPresentation,
    ReasoningEffort,
)
from backend.features.llm.infrastructure.chat_models import LLMChatModels
from backend.features.llm.infrastructure.credentials import LLMCredentials

_CHAT_MODELS_MODULE = "backend.features.llm.infrastructure.chat_models"


def _model_info(provider: LLMProvider, model_id: str = "a-model-id") -> LLMModelInfo:
    return LLMModelInfo(
        id=model_id,
        provider_model="a-model-added-only-in-yaml",
        provider=provider,
        presentation=ModelPresentation(label="Model", profile="Fast", order=10),
        capabilities=ModelCapabilities(reasoning_effort=(ReasoningEffort.MEDIUM,)),
        defaults=ModelDefaults(reasoning_effort=ReasoningEffort.MEDIUM),
    )


@pytest.fixture
def codex_provider(monkeypatch: pytest.MonkeyPatch) -> list[int]:
    """Replace the provider so tests never read a real Codex login."""
    created: list[int] = []

    def create() -> OpenAIProvider:
        created.append(1)
        return OpenAIProvider(api_key="unused")

    monkeypatch.setattr(f"{_CHAT_MODELS_MODULE}.OpenAICodexProvider", create)
    return created


def test_openai_provider_uses_the_configured_api_key() -> None:
    chat_models = LLMChatModels(LLMCredentials(openai_api_key="key"))

    model = chat_models.get(_model_info(LLMProvider.OPENAI))

    assert isinstance(model, OpenAIResponsesModel)
    assert not isinstance(model, OpenAICodexModel)
    assert model.model_name == "a-model-added-only-in-yaml"
    assert model.client.api_key == "key"
    assert model.settings is not None
    assert model.settings["openai_reasoning_effort"] == "medium"


@pytest.mark.parametrize("api_key", [None, "openai-key"])
def test_codex_provider_uses_subscription_credentials(
    codex_provider: list[int],
    api_key: str | None,
) -> None:
    chat_models = LLMChatModels(LLMCredentials(openai_api_key=api_key))

    model = chat_models.get(_model_info(LLMProvider.CODEX))

    assert isinstance(model, OpenAICodexModel)
    assert model.settings is not None
    assert model.settings["openai_reasoning_effort"] == "medium"
    assert codex_provider == [1]


def test_codex_sends_the_system_prompt_as_instructions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bodies: list[dict] = []

    def reject(request: httpx2.Request) -> httpx2.Response:
        bodies.append(json.loads(request.content))
        return httpx2.Response(400, json={"error": {"message": "stop"}})

    client = AsyncOpenAI(
        api_key="unused",
        max_retries=0,
        http_client=httpx2.AsyncClient(transport=httpx2.MockTransport(reject)),
    )
    monkeypatch.setattr(
        f"{_CHAT_MODELS_MODULE}.OpenAICodexProvider",
        lambda: OpenAICodexProvider(openai_client=client),
    )
    model = LLMChatModels(LLMCredentials(openai_api_key=None)).get(
        _model_info(LLMProvider.CODEX)
    )
    messages = [
        ModelRequest([SystemPromptPart("The system prompt")]),
        ModelRequest([UserPromptPart("Hallo")]),
    ]

    async def send() -> None:
        async with model_request_stream(model, messages):
            pass

    with pytest.raises(ModelHTTPError):
        asyncio.run(send())

    assert bodies[0]["instructions"] == "The system prompt"
    assert [item["role"] for item in bodies[0]["input"]] == ["user"]


def test_openai_provider_without_api_key_fails() -> None:
    chat_models = LLMChatModels(LLMCredentials(openai_api_key=None))

    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        chat_models.get(_model_info(LLMProvider.OPENAI))


def test_get_reuses_one_client_per_model(codex_provider: list[int]) -> None:
    chat_models = LLMChatModels(LLMCredentials(openai_api_key=None))

    first = chat_models.get(_model_info(LLMProvider.CODEX, "luna"))
    again = chat_models.get(_model_info(LLMProvider.CODEX, "luna"))
    other = chat_models.get(_model_info(LLMProvider.CODEX, "terra"))

    assert first is again
    assert other is not first
    assert len(codex_provider) == 2


def test_aclose_closes_every_created_client() -> None:
    chat_models = LLMChatModels(LLMCredentials(openai_api_key="key"))
    created = [
        chat_models.get(_model_info(LLMProvider.OPENAI, model_id))
        for model_id in ("luna", "terra")
    ]

    asyncio.run(chat_models.aclose())

    assert [model.client.is_closed() for model in created] == [True, True]
