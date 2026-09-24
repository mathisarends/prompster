from pathlib import Path

import yaml

from backend.features.llm.domain import LLMConfig, LLMRegistry


def load_llm_registry(path: Path) -> LLMRegistry:
    with path.open(encoding="utf-8") as config_file:
        raw_config = yaml.safe_load(config_file)
    return LLMRegistry(LLMConfig.model_validate(raw_config))
