import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from dataclasses import replace
from typing import Any

from pydantic_ai import RunContext
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    SystemPromptPart,
)
from pydantic_ai.models import Model, ModelRequestParameters, StreamedResponse
from pydantic_ai.models.openai import (
    OpenAIResponsesModel,
    OpenAIResponsesModelSettings,
)
from pydantic_ai.models.openai_codex import OpenAICodexModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.providers.openai_codex import OpenAICodexProvider
from pydantic_ai.settings import ModelSettings

from backend.features.llm.application import ChatModels
from backend.features.llm.domain import LLMModelInfo, LLMProvider
from backend.features.llm.infrastructure.credentials import LLMCredentials

_REQUEST_TIMEOUT_SECONDS = 60.0


class CodexChatModel(OpenAICodexModel):
    """Sends a leading system prompt in the ``instructions`` field.

    harnessed passes the system prompt as a message, while the Codex endpoint
    takes it from ``instructions``.
    """

    async def request(
        self,
        messages: list[ModelMessage],
        model_settings: ModelSettings | None,
        model_request_parameters: ModelRequestParameters,
    ) -> ModelResponse:
        return await super().request(
            _system_prompt_as_instructions(messages),
            model_settings,
            model_request_parameters,
        )

    @asynccontextmanager
    async def request_stream(
        self,
        messages: list[ModelMessage],
        model_settings: ModelSettings | None,
        model_request_parameters: ModelRequestParameters,
        run_context: RunContext[Any] | None = None,
    ) -> AsyncGenerator[StreamedResponse]:
        async with super().request_stream(
            _system_prompt_as_instructions(messages),
            model_settings,
            model_request_parameters,
            run_context,
        ) as stream:
            yield stream


class LLMChatModels(ChatModels):
    """Available application models are owned by LLMRegistry."""

    def __init__(self, credentials: LLMCredentials) -> None:
        self._credentials = credentials
        self._models: dict[str, Model] = {}

    def get(self, model: LLMModelInfo) -> Model:
        chat_model = self._models.get(model.id)
        if chat_model is None:
            chat_model = self._create(model)
            self._models[model.id] = chat_model
        return chat_model

    async def aclose(self) -> None:
        models = list(self._models.values())
        self._models.clear()
        await asyncio.gather(*(_close(model) for model in models))

    def _create(self, model: LLMModelInfo) -> Model:
        settings = _model_settings(model)
        match model.provider:
            case LLMProvider.OPENAI:
                return OpenAIResponsesModel(
                    model.provider_model,
                    provider=OpenAIProvider(api_key=self._openai_api_key()),
                    settings=settings,
                )
            case LLMProvider.CODEX:
                return CodexChatModel(
                    model.provider_model,
                    provider=OpenAICodexProvider(),
                    settings=settings,
                )

    def _openai_api_key(self) -> str:
        credential = self._credentials.openai_api_key
        api_key = credential.get_secret_value() if credential is not None else ""
        if not api_key:
            raise ValueError("OPENAI_API_KEY is required for OpenAI models.")
        return api_key


def _model_settings(model: LLMModelInfo) -> OpenAIResponsesModelSettings:
    settings = OpenAIResponsesModelSettings(timeout=_REQUEST_TIMEOUT_SECONDS)
    default_effort = model.defaults.reasoning_effort
    if default_effort is not None:
        settings["openai_reasoning_effort"] = default_effort.value
    return settings


def _system_prompt_as_instructions(
    messages: list[ModelMessage],
) -> list[ModelMessage]:
    first = messages[0] if messages else None
    if (
        not isinstance(first, ModelRequest)
        or len(first.parts) != 1
        or not isinstance(first.parts[0], SystemPromptPart)
    ):
        return messages
    instructions = first.parts[0].content
    return [_with_instructions(message, instructions) for message in messages[1:]]


def _with_instructions(message: ModelMessage, instructions: str) -> ModelMessage:
    if isinstance(message, ModelRequest):
        return replace(message, instructions=instructions)
    return message


async def _close(model: Model) -> None:
    # Leaving the outermost model context closes the client its provider owns.
    async with model:
        pass
