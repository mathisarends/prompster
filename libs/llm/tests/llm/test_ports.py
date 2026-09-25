from collections.abc import AsyncIterator, Sequence

import pytest
from pydantic import BaseModel, TypeAdapter

from llm import (
    AssistantMessage,
    ChatModel,
    Message,
    MessageType,
    ModelError,
    ModelEvent,
    ModelEventType,
    ModelResponse,
    ModelTool,
    TextDelta,
    UserMessage,
)


class _Title(BaseModel):
    title: str


class _FixedCompletionModel(ChatModel):
    def __init__(self, completion: str) -> None:
        self._completion = completion
        self.output_types: list[type[BaseModel] | None] = []

    async def stream(
        self,
        messages: Sequence[Message],
        *,
        tools: Sequence[ModelTool] = (),
    ) -> AsyncIterator[ModelEvent]:
        yield ModelResponse(completion=self._completion)

    async def _call(
        self,
        messages: Sequence[Message],
        *,
        tools: Sequence[ModelTool],
        output_type: type[BaseModel] | None,
    ) -> ModelResponse:
        self.output_types.append(output_type)
        return ModelResponse(completion=self._completion)

    async def aclose(self) -> None:
        return None


def test_message_discriminator_deserializes_to_the_concrete_message() -> None:
    adapter = TypeAdapter(Message)

    message = adapter.validate_python({"type": "user", "content": "Hello"})

    assert message == UserMessage(content="Hello")
    assert message.type is MessageType.USER


def test_model_event_discriminator_deserializes_to_the_concrete_event() -> None:
    adapter = TypeAdapter(ModelEvent)

    event = adapter.validate_python({"type": "text_delta", "delta": "Hello"})

    assert event == TextDelta(delta="Hello")
    assert event.type is ModelEventType.TEXT_DELTA


def test_provider_state_is_not_serialized() -> None:
    message = AssistantMessage(content="Hi", provider_state=object())

    assert "provider_state" not in message.model_dump()


async def test_call_without_output_type_returns_the_model_response() -> None:
    model = _FixedCompletionModel("Plain answer")

    response = await model.call([UserMessage(content="Question")])

    assert response == ModelResponse(completion="Plain answer")
    assert model.output_types == [None]


async def test_call_with_output_type_returns_the_parsed_output() -> None:
    model = _FixedCompletionModel('{"title": "Summer Hits"}')

    output = await model.call([UserMessage(content="Name it")], output_type=_Title)

    assert output == _Title(title="Summer Hits")
    assert model.output_types == [_Title]


async def test_call_with_mismatching_output_raises_model_error() -> None:
    model = _FixedCompletionModel("not json")

    with pytest.raises(ModelError, match="_Title"):
        await model.call([UserMessage(content="Name it")], output_type=_Title)
