import asyncio

from llm import LLMProvider
from llm.registry import DEFAULT_OPENAI_MODEL, OPENAI_MODELS

from backend.features.llm_options.presentation.router import list_llm_options


class TestListLlmOptionsRoute:
    def test_returns_supported_models_with_default_marker(self) -> None:
        response = asyncio.run(list_llm_options())

        assert [item.id for item in response.items] == [m.value for m in OPENAI_MODELS]
        assert [item.provider for item in response.items] == [LLMProvider.OPENAI] * len(
            OPENAI_MODELS
        )
        assert [item.label for item in response.items] == [
            m.value for m in OPENAI_MODELS
        ]

        defaults = [item.id for item in response.items if item.is_default]
        assert defaults == [DEFAULT_OPENAI_MODEL.value]
