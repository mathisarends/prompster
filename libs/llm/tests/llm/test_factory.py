from llm.factory import create_gpt_5_5, create_openai_llm
from llm.registry import ModelId


class _FakeCredentials:
    def __init__(self, api_key: str) -> None:
        self.openai_api_key = api_key


class _DummyChatOpenAI:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


class TestFactory:
    def test_create_openai_llm_passes_selected_options(self, monkeypatch) -> None:
        monkeypatch.setattr("llm.factory.ChatOpenAI", _DummyChatOpenAI)

        llm = create_openai_llm(
            model=ModelId.GPT_5_4_MINI,
            api_key="abc123",
            temperature=0.2,
            max_tokens=256,
            top_p=0.95,
        )

        assert isinstance(llm, _DummyChatOpenAI)
        assert llm.kwargs == {
            "model": ModelId.GPT_5_4_MINI,
            "api_key": "abc123",
            "temperature": 0.2,
            "max_tokens": 256,
            "top_p": 0.95,
        }

    def test_create_openai_llm_reads_api_key_from_credentials(
        self, monkeypatch
    ) -> None:
        monkeypatch.setattr("llm.factory.ChatOpenAI", _DummyChatOpenAI)
        credentials = _FakeCredentials("from-credentials")

        llm = create_openai_llm(
            model=ModelId.GPT_5_4,
            credentials=credentials,
        )

        assert isinstance(llm, _DummyChatOpenAI)
        assert llm.kwargs == {
            "model": ModelId.GPT_5_4,
            "api_key": "from-credentials",
        }

    def test_create_openai_llm_prefers_explicit_api_key_over_credentials(
        self, monkeypatch
    ) -> None:
        monkeypatch.setattr("llm.factory.ChatOpenAI", _DummyChatOpenAI)
        credentials = _FakeCredentials("from-credentials")

        llm = create_openai_llm(
            model=ModelId.GPT_5_4,
            api_key="explicit-key",
            credentials=credentials,
        )

        assert isinstance(llm, _DummyChatOpenAI)
        assert llm.kwargs == {
            "model": ModelId.GPT_5_4,
            "api_key": "explicit-key",
        }

    def test_create_openai_llm_builds_credentials_when_missing(
        self, monkeypatch
    ) -> None:
        monkeypatch.setattr("llm.factory.ChatOpenAI", _DummyChatOpenAI)

        class _AutoCredentials:
            openai_api_key = "from-default-settings"

        monkeypatch.setattr("llm.factory.LLMCredentials", lambda: _AutoCredentials())

        llm = create_openai_llm(model=ModelId.GPT_5_4)

        assert isinstance(llm, _DummyChatOpenAI)
        assert llm.kwargs == {
            "model": ModelId.GPT_5_4,
            "api_key": "from-default-settings",
        }

    def test_create_gpt_5_5_uses_fixed_model_and_credentials(self, monkeypatch) -> None:
        monkeypatch.setattr("llm.factory.ChatOpenAI", _DummyChatOpenAI)
        credentials = _FakeCredentials("factory-key")

        llm = create_gpt_5_5(credentials=credentials)

        assert isinstance(llm, _DummyChatOpenAI)
        assert llm.kwargs == {
            "model": ModelId.GPT_5_5,
            "api_key": "factory-key",
        }
