import pytest
from llm import ReasoningEffort

from backend.features.llm.domain import (
    LLMModelInfo,
    LLMProvider,
    ModelCapabilities,
    ModelDefaults,
    ModelPresentation,
)
from backend.features.llm.domain import ReasoningEffort as ModelReasoningEffort
from backend.features.llm.infrastructure.chat_model_factory import LLMChatModelFactory
from backend.features.llm.infrastructure.credentials import LLMCredentials

_FACTORY_MODULE = "backend.features.llm.infrastructure.chat_model_factory"


def _model_info(provider: LLMProvider) -> LLMModelInfo:
    return LLMModelInfo(
        id="a-model-id",
        provider_model="a-model-added-only-in-yaml",
        provider=provider,
        presentation=ModelPresentation(label="Model", profile="Fast", order=10),
        capabilities=ModelCapabilities(reasoning_effort=(ModelReasoningEffort.MEDIUM,)),
        defaults=ModelDefaults(reasoning_effort=ModelReasoningEffort.MEDIUM),
    )


def _record_calls(monkeypatch: pytest.MonkeyPatch, name: str) -> list[dict]:
    calls: list[dict] = []

    def create(model_name: str, **kwargs: object) -> object:
        calls.append({"model_name": model_name, **kwargs})
        return object()

    monkeypatch.setattr(f"{_FACTORY_MODULE}.{name}", create)
    return calls


def test_openai_provider_uses_the_configured_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _record_calls(monkeypatch, "create_openai_model")
    factory = LLMChatModelFactory(LLMCredentials(openai_api_key="key"))

    factory.create(_model_info(LLMProvider.OPENAI))

    assert calls == [
        {
            "model_name": "a-model-added-only-in-yaml",
            "api_key": "key",
            "reasoning_effort": ReasoningEffort.MEDIUM,
        }
    ]


def test_codex_provider_needs_no_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _record_calls(monkeypatch, "create_codex_model")
    factory = LLMChatModelFactory(LLMCredentials(openai_api_key=None))

    factory.create(_model_info(LLMProvider.CODEX))

    assert calls == [
        {
            "model_name": "a-model-added-only-in-yaml",
            "reasoning_effort": ReasoningEffort.MEDIUM,
        }
    ]


def test_openai_provider_without_api_key_fails() -> None:
    factory = LLMChatModelFactory(LLMCredentials(openai_api_key=None))

    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        factory.create(_model_info(LLMProvider.OPENAI))
