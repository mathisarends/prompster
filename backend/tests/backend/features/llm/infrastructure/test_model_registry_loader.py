from pathlib import Path

import pytest
from pydantic import ValidationError

from backend.features.llm.infrastructure.model_registry_loader import (
    load_llm_registry,
)


def _write_config(path: Path, *, default_model_id: str = "fast") -> Path:
    path.write_text(
        f"""
version: 1
default_model_id: {default_model_id}
models:
  - id: smart
    provider_model: provider-smart
    enabled: false
    presentation:
      label: Smart
      profile: Intelligent
      order: 20
  - id: fast
    provider_model: provider-fast
    enabled: true
    presentation:
      label: Fast
      profile: Schnell
      order: 10
    capabilities:
      reasoning_effort: [low, medium, high]
    defaults:
      reasoning_effort: medium
""".strip(),
        encoding="utf-8",
    )
    return path


class TestLLMConfiguration:
    def test_loads_available_models_and_provider_mapping(self, tmp_path: Path) -> None:
        registry = load_llm_registry(_write_config(tmp_path / "models.yml"))

        assert [model.id for model in registry.available_models] == ["fast"]
        assert registry.default_model.id == "fast"
        assert registry.get("fast").provider_model == "provider-fast"

    def test_rejects_a_disabled_default(self, tmp_path: Path) -> None:
        path = _write_config(tmp_path / "models.yml", default_model_id="smart")

        with pytest.raises(ValidationError, match="must be enabled"):
            load_llm_registry(path)

    def test_rejects_an_unknown_model(self, tmp_path: Path) -> None:
        registry = load_llm_registry(_write_config(tmp_path / "models.yml"))

        with pytest.raises(ValueError, match="Unsupported LLM model"):
            registry.get("missing")
