from pathlib import Path

from backend.features.llm.application import ChatModelFactory
from backend.features.llm.domain import LLMRegistry
from backend.features.llm.infrastructure.credentials import LLMCredentials
from backend.features.llm.infrastructure.model_registry_loader import (
    load_llm_registry,
)
from backend.features.llm.infrastructure.chat_model_factory import (
    LLMChatModelFactory,
)
from dishka import Provider, Scope, provide
from llm import ChatModel

_LLM_CONFIG_PATH = Path(__file__).parents[1] / "models.yml"


class LLMFeatureProvider(Provider):
    @provide(scope=Scope.APP)
    def registry(self) -> LLMRegistry:
        return load_llm_registry(_LLM_CONFIG_PATH)

    @provide(scope=Scope.APP)
    def credentials(self) -> LLMCredentials:
        return LLMCredentials()

    @provide(scope=Scope.APP)
    def chat_model_factory(self, credentials: LLMCredentials) -> ChatModelFactory:
        return LLMChatModelFactory(credentials=credentials)

    @provide(scope=Scope.APP)
    def default_llm(
        self,
        registry: LLMRegistry,
        chat_models: ChatModelFactory,
    ) -> ChatModel:
        return chat_models.create(registry.default_model)
