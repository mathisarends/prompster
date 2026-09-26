from collections.abc import AsyncGenerator
from pathlib import Path

from backend.features.llm.application import ChatModels
from backend.features.llm.domain import LLMRegistry
from backend.features.llm.infrastructure.credentials import LLMCredentials
from backend.features.llm.infrastructure.model_registry_loader import (
    load_llm_registry,
)
from backend.features.llm.infrastructure.chat_models import LLMChatModels
from dishka import Provider, Scope, provide
from callm import ChatModel

_LLM_CONFIG_PATH = Path(__file__).parents[1] / "models.yml"


class LLMFeatureProvider(Provider):
    @provide(scope=Scope.APP)
    def registry(self) -> LLMRegistry:
        return load_llm_registry(_LLM_CONFIG_PATH)

    @provide(scope=Scope.APP)
    def credentials(self) -> LLMCredentials:
        return LLMCredentials()

    @provide(scope=Scope.APP)
    async def chat_models(
        self,
        credentials: LLMCredentials,
    ) -> AsyncGenerator[ChatModels]:
        chat_models = LLMChatModels(credentials=credentials)
        try:
            yield chat_models
        finally:
            await chat_models.aclose()

    @provide(scope=Scope.APP)
    def default_llm(
        self,
        registry: LLMRegistry,
        chat_models: ChatModels,
    ) -> ChatModel:
        return chat_models.get(registry.default_model)
