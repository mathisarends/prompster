from llm import ChatModel, ReasoningEffort, create_codex_model, create_openai_model

from backend.features.llm.application import ChatModelFactory
from backend.features.llm.domain import LLMModelInfo, LLMProvider
from backend.features.llm.infrastructure.credentials import LLMCredentials


class LLMChatModelFactory(ChatModelFactory):
    """Create a client; available application models are owned by LLMRegistry."""

    def __init__(self, credentials: LLMCredentials) -> None:
        self._credentials = credentials

    def create(self, model: LLMModelInfo) -> ChatModel:
        reasoning_effort = _reasoning_effort(model)
        match model.provider:
            case LLMProvider.OPENAI:
                return create_openai_model(
                    model.provider_model,
                    api_key=self._openai_api_key(),
                    reasoning_effort=reasoning_effort,
                )
            case LLMProvider.CODEX:
                return create_codex_model(
                    model.provider_model,
                    reasoning_effort=reasoning_effort,
                )

    def _openai_api_key(self) -> str:
        api_key = self._credentials.openai_api_key
        if not api_key:
            raise ValueError("OPENAI_API_KEY is required for OpenAI models.")
        return api_key


def _reasoning_effort(model: LLMModelInfo) -> ReasoningEffort | None:
    default = model.defaults.reasoning_effort
    return ReasoningEffort(default.value) if default is not None else None
