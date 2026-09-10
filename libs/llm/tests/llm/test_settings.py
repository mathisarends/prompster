import pytest
from pydantic import ValidationError

from llm.credentials import LLMCredentials


class TestSettings:
    def test_llm_credentials_raise_when_api_key_missing(self, monkeypatch) -> None:
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        with pytest.raises(ValidationError):
            LLMCredentials(_env_file=None)

    def test_llm_credentials_read_api_key_from_environment(self, monkeypatch) -> None:
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key")

        credentials = LLMCredentials(_env_file=None)

        assert credentials.openai_api_key == "test-api-key"
