import asyncio

import pytest
from callm import ReasoningEffort

from backend.features.llm.domain import (
    LLMModelInfo,
    LLMProvider,
    ModelCapabilities,
    ModelDefaults,
    ModelPresentation,
)
from backend.features.llm.domain import ReasoningEffort as ModelReasoningEffort
from backend.features.llm.infrastructure.chat_models import LLMChatModels
from backend.features.llm.infrastructure.credentials import LLMCredentials

_CHAT_MODELS_MODULE = "backend.features.llm.infrastructure.chat_models"


class _ChatModelStub:
    def __init__(self) -> None:
        self.closed = False

    async def aclose(self) -> None:
        self.closed = True


def _model_info(provider: LLMProvider, model_id: str = "a-model-id") -> LLMModelInfo:
    return LLMModelInfo(
        id=model_id,
        provider_model="a-model-added-only-in-yaml",
        provider=provider,
        presentation=ModelPresentation(label="Model", profile="Fast", order=10),
        capabilities=ModelCapabilities(reasoning_effort=(ModelReasoningEffort.MEDIUM,)),
        defaults=ModelDefaults(reasoning_effort=ModelReasoningEffort.MEDIUM),
    )


def _record_calls(monkeypatch: pytest.MonkeyPatch, name: str) -> list[dict]:
    calls: list[dict] = []

    def create(model_name: str, **kwargs: object) -> _ChatModelStub:
        calls.append({"model_name": model_name, **kwargs})
        return _ChatModelStub()

    monkeypatch.setattr(f"{_CHAT_MODELS_MODULE}.{name}", create)
    return calls


def test_openai_provider_uses_the_configured_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _record_calls(monkeypatch, "ChatOpenAIResponses")
    chat_models = LLMChatModels(LLMCredentials(openai_api_key="key"))

    chat_models.get(_model_info(LLMProvider.OPENAI))

    assert calls == [
        {
            "model_name": "a-model-added-only-in-yaml",
            "api_key": "key",
            "reasoning_effort": ReasoningEffort.MEDIUM,
        }
    ]


def test_codex_provider_needs_no_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _record_calls(monkeypatch, "ChatCodex")
    chat_models = LLMChatModels(LLMCredentials(openai_api_key=None))

    chat_models.get(_model_info(LLMProvider.CODEX))

    assert calls == [
        {
            "model_name": "a-model-added-only-in-yaml",
            "reasoning_effort": ReasoningEffort.MEDIUM,
        }
    ]


def test_openai_provider_without_api_key_fails() -> None:
    chat_models = LLMChatModels(LLMCredentials(openai_api_key=None))

    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        chat_models.get(_model_info(LLMProvider.OPENAI))


def test_get_reuses_one_client_per_model(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _record_calls(monkeypatch, "ChatCodex")
    chat_models = LLMChatModels(LLMCredentials(openai_api_key=None))

    first = chat_models.get(_model_info(LLMProvider.CODEX, "luna"))
    again = chat_models.get(_model_info(LLMProvider.CODEX, "luna"))
    other = chat_models.get(_model_info(LLMProvider.CODEX, "terra"))

    assert first is again
    assert other is not first
    assert len(calls) == 2


def test_aclose_closes_every_created_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _record_calls(monkeypatch, "ChatCodex")
    chat_models = LLMChatModels(LLMCredentials(openai_api_key=None))
    created = [
        chat_models.get(_model_info(LLMProvider.CODEX, model_id))
        for model_id in ("luna", "terra")
    ]

    asyncio.run(chat_models.aclose())

    assert all(model.closed for model in created)
