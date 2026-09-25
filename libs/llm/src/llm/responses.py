from collections.abc import AsyncIterator, Iterator, Sequence
from contextlib import contextmanager
from enum import StrEnum

from pydantic import BaseModel
from pydantic_ai.exceptions import ModelAPIError, ModelHTTPError
from pydantic_ai.messages import (
    BinaryContent,
    ModelRequest,
    PartDeltaEvent,
    PartStartEvent,
    TextPart,
    TextPartDelta,
    ToolCallPart,
    ToolReturnPart,
    UserContent,
    UserPromptPart,
)
from pydantic_ai.messages import ModelMessage as PydanticMessage
from pydantic_ai.messages import ModelResponse as PydanticResponse
from pydantic_ai.models import ModelRequestParameters
from pydantic_ai.models.openai import (
    OpenAIResponsesModel,
    OpenAIResponsesModelSettings,
)
from pydantic_ai.models.openai_codex import OpenAICodexModel
from pydantic_ai.output import OutputObjectDefinition
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.providers.openai_codex import OpenAICodexProvider
from pydantic_ai.tools import ToolDefinition
from pydantic_ai.usage import RequestUsage

from llm.ports import (
    AssistantMessage,
    ChatModel,
    ContextLengthExceededError,
    Message,
    ModelError,
    ModelEvent,
    ModelResponse,
    ModelTool,
    SystemMessage,
    TextDelta,
    ToolCall,
    ToolResultMessage,
    Usage,
    UserMessage,
)

_CONTEXT_LENGTH_EXCEEDED = "context_length_exceeded"


class ReasoningEffort(StrEnum):
    NONE = "none"
    MINIMAL = "minimal"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    XHIGH = "xhigh"


class ResponsesChatModel(ChatModel):
    """ChatModel over a Pydantic AI OpenAI Responses model via HTTP."""

    def __init__(
        self,
        model: OpenAIResponsesModel,
        *,
        reasoning_effort: ReasoningEffort | None = None,
    ) -> None:
        self._model = model
        self._settings = OpenAIResponsesModelSettings()
        if reasoning_effort is not None:
            self._settings["openai_reasoning_effort"] = reasoning_effort.value

    @property
    def model_name(self) -> str:
        return self._model.model_name

    async def stream(
        self,
        messages: Sequence[Message],
        *,
        tools: Sequence[ModelTool] = (),
    ) -> AsyncIterator[ModelEvent]:
        with _translate_errors():
            async with self._model.request_stream(
                _pydantic_messages(messages),
                self._settings,
                _request_parameters(tools),
            ) as response:
                async for event in response:
                    delta = _text_delta(event)
                    if delta:
                        yield TextDelta(delta=delta)
                final = response.get()
        yield _model_response(final)

    async def _call(
        self,
        messages: Sequence[Message],
        *,
        tools: Sequence[ModelTool],
        output_type: type[BaseModel] | None,
    ) -> ModelResponse:
        with _translate_errors():
            response = await self._model.request(
                _pydantic_messages(messages),
                self._settings,
                _request_parameters(tools, output_type),
            )
        return _model_response(response)

    async def aclose(self) -> None:
        await self._model.client.close()


def create_openai_model(
    model_name: str,
    *,
    api_key: str,
    reasoning_effort: ReasoningEffort | None = None,
) -> ResponsesChatModel:
    provider = OpenAIProvider(api_key=api_key)
    return ResponsesChatModel(
        OpenAIResponsesModel(model_name, provider=provider),
        reasoning_effort=reasoning_effort,
    )


def create_codex_model(
    model_name: str,
    *,
    reasoning_effort: ReasoningEffort | None = None,
) -> ResponsesChatModel:
    """Use the ChatGPT subscription login of the local Codex CLI."""
    return ResponsesChatModel(
        OpenAICodexModel(model_name, provider=OpenAICodexProvider()),
        reasoning_effort=reasoning_effort,
    )


@contextmanager
def _translate_errors() -> Iterator[None]:
    try:
        yield
    except ModelHTTPError as error:
        if _CONTEXT_LENGTH_EXCEEDED in str(error.body):
            raise ContextLengthExceededError(str(error)) from error
        raise ModelError(str(error)) from error
    except ModelAPIError as error:
        raise ModelError(str(error)) from error


def _request_parameters(
    tools: Sequence[ModelTool],
    output_type: type[BaseModel] | None = None,
) -> ModelRequestParameters:
    function_tools = [_tool_definition(tool) for tool in tools]
    if output_type is None:
        return ModelRequestParameters(function_tools=function_tools)
    return ModelRequestParameters(
        function_tools=function_tools,
        output_mode="native",
        output_object=OutputObjectDefinition(
            json_schema=output_type.model_json_schema(),
            name=output_type.__name__,
            strict=True,
        ),
    )


def _model_response(response: PydanticResponse) -> ModelResponse:
    return ModelResponse(
        completion="".join(
            part.content for part in response.parts if isinstance(part, TextPart)
        ),
        finish_reason=response.finish_reason or "stop",
        tool_calls=tuple(
            ToolCall(
                id=part.tool_call_id,
                name=part.tool_name,
                arguments=part.args_as_json_str(),
            )
            for part in response.parts
            if isinstance(part, ToolCallPart)
        ),
        usage=_usage(response.usage),
        provider_state=response,
    )


def _usage(usage: RequestUsage) -> Usage:
    return Usage(
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens,
        cache_read_tokens=usage.cache_read_tokens,
    )


def _tool_definition(tool: ModelTool) -> ToolDefinition:
    return ToolDefinition(
        name=tool.name,
        description=tool.description or None,
        parameters_json_schema=tool.parameters,
    )


def _pydantic_messages(messages: Sequence[Message]) -> list[PydanticMessage]:
    instructions: str | None = None
    converted: list[PydanticMessage] = []
    for message in messages:
        match message:
            case SystemMessage():
                instructions = message.content
            case UserMessage():
                converted.append(
                    ModelRequest(
                        parts=[UserPromptPart(_user_content(message))],
                        instructions=instructions,
                    )
                )
            case AssistantMessage(provider_state=PydanticResponse() as state):
                converted.append(state)
            case AssistantMessage():
                parts: list[TextPart | ToolCallPart] = []
                if message.content:
                    parts.append(TextPart(message.content))
                parts.extend(
                    ToolCallPart(call.name, call.arguments, call.id)
                    for call in message.tool_calls
                )
                converted.append(PydanticResponse(parts=parts))
            case ToolResultMessage():
                converted.append(
                    ModelRequest(
                        parts=[
                            ToolReturnPart(
                                message.tool_name,
                                message.content,
                                message.tool_call_id,
                                outcome="failed" if message.is_error else "success",
                            )
                        ],
                        instructions=instructions,
                    )
                )
    return converted


def _user_content(message: UserMessage) -> str | list[UserContent]:
    if not message.images:
        return message.content
    content: list[UserContent] = [message.content]
    content.extend(
        BinaryContent(data=image.data, media_type=image.media_type)
        for image in message.images
    )
    return content


def _text_delta(event: object) -> str:
    if isinstance(event, PartStartEvent) and isinstance(event.part, TextPart):
        return event.part.content
    if isinstance(event, PartDeltaEvent) and isinstance(event.delta, TextPartDelta):
        return event.delta.content_delta
    return ""
