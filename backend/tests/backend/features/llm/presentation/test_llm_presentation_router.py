import asyncio
from pathlib import Path

from backend.features.llm.domain import LLMProvider
from backend.features.llm.infrastructure.model_registry_loader import (
    load_llm_registry,
)
from backend.features.llm.presentation.router import list_llm_options

_CONFIG_PATH = (
    Path(__file__).parents[5] / "src" / "backend" / "features" / "llm" / "models.yml"
)


class TestListLlmOptionsRoute:
    def test_returns_enabled_models_in_presentation_order(self) -> None:
        registry = load_llm_registry(_CONFIG_PATH)

        response = asyncio.run(list_llm_options(registry))

        assert [item.id for item in response.items] == [
            "gpt-5.6-luna-US",
            "gpt-5.6-terra-US",
        ]
        assert [item.provider for item in response.items] == [
            LLMProvider.OPENAI,
            LLMProvider.OPENAI,
        ]
        assert [item.label for item in response.items] == [
            "GPT 5.6 Luna",
            "GPT 5.6 Terra",
        ]
        assert [item.profile for item in response.items] == ["Schnell", "Intelligent"]
        assert [item.id for item in response.items if item.is_default] == [
            "gpt-5.6-luna-US"
        ]
