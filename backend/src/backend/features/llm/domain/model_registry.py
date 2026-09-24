from collections.abc import Sequence
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class LLMProvider(StrEnum):
    OPENAI = "openai"


class ReasoningEffort(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ModelPresentation(BaseModel):
    model_config = ConfigDict(frozen=True)

    label: str = Field(min_length=1)
    profile: str = Field(min_length=1)
    order: int


class ModelCapabilities(BaseModel):
    model_config = ConfigDict(frozen=True)

    temperature: bool = False
    reasoning_effort: tuple[ReasoningEffort, ...] = ()


class ModelDefaults(BaseModel):
    model_config = ConfigDict(frozen=True)

    reasoning_effort: ReasoningEffort | None = None


class LLMModelInfo(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str = Field(min_length=1)
    provider_model: str = Field(min_length=1)
    provider: LLMProvider = LLMProvider.OPENAI
    enabled: bool = True
    presentation: ModelPresentation
    capabilities: ModelCapabilities = ModelCapabilities()
    defaults: ModelDefaults = ModelDefaults()
    input_token_limit: int = Field(default=272_000, gt=0)

    @model_validator(mode="after")
    def default_reasoning_effort_is_supported(self) -> LLMModelInfo:
        default = self.defaults.reasoning_effort
        if default is not None and default not in self.capabilities.reasoning_effort:
            msg = (
                f"Default reasoning effort '{default}' is not supported by model "
                f"'{self.id}'."
            )
            raise ValueError(msg)
        return self


class LLMConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    version: Literal[1]
    default_model_id: str = Field(min_length=1)
    models: tuple[LLMModelInfo, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def model_ids_are_unique_and_default_is_enabled(self) -> LLMConfig:
        ids = [model.id for model in self.models]
        if len(ids) != len(set(ids)):
            raise ValueError("LLM model ids must be unique.")

        default = next(
            (model for model in self.models if model.id == self.default_model_id),
            None,
        )
        if default is None:
            raise ValueError(
                f"Default model '{self.default_model_id}' is not configured."
            )
        if not default.enabled:
            raise ValueError(
                f"Default model '{self.default_model_id}' must be enabled."
            )
        return self


class LLMRegistry:
    """Runtime catalogue of the models users can choose from."""

    def __init__(self, config: LLMConfig) -> None:
        self._config = config
        self._models = {model.id: model for model in config.models}

    @property
    def default_model(self) -> LLMModelInfo:
        return self._models[self._config.default_model_id]

    @property
    def available_models(self) -> Sequence[LLMModelInfo]:
        return tuple(
            sorted(
                (model for model in self._config.models if model.enabled),
                key=lambda model: model.presentation.order,
            )
        )

    def get(self, model_id: str) -> LLMModelInfo:
        model = self._models.get(model_id)
        if model is not None and model.enabled:
            return model
        supported_models = ", ".join(model.id for model in self.available_models)
        msg = (
            f"Unsupported LLM model '{model_id}'. Supported models: {supported_models}."
        )
        raise ValueError(msg)
