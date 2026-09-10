from pathlib import Path

from backend.features.llm.configuration import LLMRegistry, load_llm_registry
from backend.features.llm.credentials import LLMCredentials
from backend.features.llm.factory import create_openai_llm
from dishka import Provider, Scope, provide
from llmify import ChatModel

_LLM_CONFIG_PATH = Path(__file__).parents[1] / "models.yml"


class LLMFeatureProvider(Provider):
    @provide(scope=Scope.APP)
    def registry(self) -> LLMRegistry:
        return load_llm_registry(_LLM_CONFIG_PATH)

    @provide(scope=Scope.APP)
    def credentials(self) -> LLMCredentials:
        return LLMCredentials()

    @provide(scope=Scope.APP)
    def default_llm(
        self,
        registry: LLMRegistry,
        credentials: LLMCredentials,
    ) -> ChatModel:
        return create_openai_llm(
            provider_model=registry.default_model.provider_model,
            credentials=credentials,
        )
