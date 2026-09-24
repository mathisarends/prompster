from backend.features.llm.infrastructure.openai_chat_model_factory import (
    create_openai_llm,
)


class _FakeCredentials:
    def __init__(self, api_key: str) -> None:
        self.openai_api_key = api_key


class _DummyChatOpenAIResponses:
    def __init__(self, **kwargs: object) -> None:
        self.kwargs = kwargs


def test_factory_uses_provider_model_without_owning_model_ids(monkeypatch) -> None:
    monkeypatch.setattr(
        "backend.features.llm.infrastructure.openai_chat_model_factory.ChatOpenAIResponses",
        _DummyChatOpenAIResponses,
    )

    llm = create_openai_llm(
        provider_model="a-model-added-only-in-yaml",
        credentials=_FakeCredentials("key"),  # type: ignore[arg-type]
    )

    assert isinstance(llm, _DummyChatOpenAIResponses)
    assert llm.kwargs == {
        "model": "a-model-added-only-in-yaml",
        "api_key": "key",
    }
