from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Sequence
from enum import StrEnum
from typing import Annotated, Literal, overload

from pydantic import BaseModel, ConfigDict, Field


class ModelError(Exception):
    """Raised when a model request fails or violates the ChatModel contract."""


class ContextLengthExceededError(ModelError):
    """Raised when the request no longer fits into the model's context window."""


class MessageType(StrEnum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL_RESULT = "tool_result"


class ModelEventType(StrEnum):
    TEXT_DELTA = "text_delta"
    RESPONSE = "response"


class ToolCall(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    name: str
    arguments: str = "{}"


class Image(BaseModel):
    model_config = ConfigDict(frozen=True)

    data: bytes = Field(repr=False)
    media_type: str


class SystemMessage(BaseModel):
    model_config = ConfigDict(frozen=True)

    type: Literal[MessageType.SYSTEM] = MessageType.SYSTEM
    content: str


class UserMessage(BaseModel):
    model_config = ConfigDict(frozen=True)

    type: Literal[MessageType.USER] = MessageType.USER
    content: str
    images: tuple[Image, ...] = ()


class AssistantMessage(BaseModel):
    model_config = ConfigDict(frozen=True)

    type: Literal[MessageType.ASSISTANT] = MessageType.ASSISTANT
    content: str
    tool_calls: tuple[ToolCall, ...] = ()
    provider_state: object | None = Field(default=None, repr=False, exclude=True)


class ToolResultMessage(BaseModel):
    model_config = ConfigDict(frozen=True)

    type: Literal[MessageType.TOOL_RESULT] = MessageType.TOOL_RESULT
    tool_call_id: str
    tool_name: str
    content: str
    is_error: bool = False


type Message = Annotated[
    SystemMessage | UserMessage | AssistantMessage | ToolResultMessage,
    Field(discriminator="type"),
]


class ModelTool(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    description: str
    parameters: dict[str, object]


class Usage(BaseModel):
    model_config = ConfigDict(frozen=True)

    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


class TextDelta(BaseModel):
    model_config = ConfigDict(frozen=True)

    type: Literal[ModelEventType.TEXT_DELTA] = ModelEventType.TEXT_DELTA
    delta: str


class ModelResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    type: Literal[ModelEventType.RESPONSE] = ModelEventType.RESPONSE
    completion: str = ""
    finish_reason: str = "stop"
    tool_calls: tuple[ToolCall, ...] = ()
    usage: Usage = Usage()
    provider_state: object | None = Field(default=None, repr=False, exclude=True)


type ModelEvent = Annotated[TextDelta | ModelResponse, Field(discriminator="type")]


class ChatModel(ABC):
    @abstractmethod
    def stream(
        self,
        messages: Sequence[Message],
        *,
        tools: Sequence[ModelTool] = (),
    ) -> AsyncIterator[ModelEvent]:
        """Yield text deltas followed by exactly one final ModelResponse."""

    @overload
    async def call(
        self,
        messages: Sequence[Message],
        *,
        tools: Sequence[ModelTool] = (),
    ) -> ModelResponse: ...

    @overload
    async def call[T: BaseModel](
        self,
        messages: Sequence[Message],
        *,
        output_type: type[T],
    ) -> T: ...

    async def call(
        self,
        messages: Sequence[Message],
        *,
        tools: Sequence[ModelTool] = (),
        output_type: type[BaseModel] | None = None,
    ) -> ModelResponse | BaseModel:
        response = await self._call(messages, tools=tools, output_type=output_type)
        if output_type is None:
            return response
        try:
            return output_type.model_validate_json(response.completion)
        except ValueError as error:
            raise ModelError(
                f"Model output does not match {output_type.__name__}: {error}"
            ) from error

    @abstractmethod
    async def _call(
        self,
        messages: Sequence[Message],
        *,
        tools: Sequence[ModelTool],
        output_type: type[BaseModel] | None,
    ) -> ModelResponse: ...

    @abstractmethod
    async def aclose(self) -> None: ...
