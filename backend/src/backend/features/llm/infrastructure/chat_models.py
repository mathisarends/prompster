import asyncio

from callm import ChatCodex, ChatModel, ChatOpenAIResponses, ReasoningEffort

from backend.features.llm.application import ChatModels
from backend.features.llm.domain import LLMModelInfo, LLMProvider
from backend.features.llm.infrastructure.credentials import LLMCredentials


class LLMChatModels(ChatModels):
    """Available application models are owned by LLMRegistry."""

    def __init__(self, credentials: LLMCredentials) -> None:
        self._credentials = credentials
        self._models: dict[str, ChatModel] = {}

    def get(self, model: LLMModelInfo) -> ChatModel:
        chat_model = self._models.get(model.id)
        if chat_model is None:
            chat_model = self._create(model)
            self._models[model.id] = chat_model
        return chat_model

    async def aclose(self) -> None:
        models = list(self._models.values())
        self._models.clear()
        await asyncio.gather(*(model.aclose() for model in models))

    def _create(self, model: LLMModelInfo) -> ChatModel:
        reasoning_effort = _reasoning_effort(model)
        match model.provider:
            case LLMProvider.OPENAI:
                return ChatOpenAIResponses(
                    model.provider_model,
                    api_key=self._openai_api_key(),
                    reasoning_effort=reasoning_effort,
                )
            case LLMProvider.CODEX:
                return ChatCodex(
                    model.provider_model,
                    reasoning_effort=reasoning_effort,
                )

    def _openai_api_key(self) -> str:
        credential = self._credentials.openai_api_key
        api_key = credential.get_secret_value() if credential is not None else ""
        if not api_key:
            raise ValueError("OPENAI_API_KEY is required for OpenAI models.")
        return api_key


def _reasoning_effort(model: LLMModelInfo) -> ReasoningEffort | None:
    default = model.defaults.reasoning_effort
    return ReasoningEffort(default.value) if default is not None else None
