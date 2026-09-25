from contextlib import asynccontextmanager
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock, patch

import pytest
from pydantic import BaseModel
from pydantic_ai.exceptions import ModelHTTPError
from pydantic_ai.messages import (
    BinaryContent,
    ModelRequest,
    PartDeltaEvent,
    PartStartEvent,
    TextPart,
    TextPartDelta,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)
from pydantic_ai.messages import ModelResponse as PydanticResponse
from pydantic_ai.models.openai import OpenAIResponsesModel
from pydantic_ai.usage import RequestUsage

from llm import (
    AssistantMessage,
    ContextLengthExceededError,
    Image,
    ModelError,
    ModelResponse,
    ModelTool,
    ReasoningEffort,
    ResponsesChatModel,
    SystemMessage,
    TextDelta,
    ToolCall,
    ToolResultMessage,
    Usage,
    UserMessage,
    create_codex_model,
    create_openai_model,
)
from llm.responses import _pydantic_messages


class _Critique(BaseModel):
    verdict: str


def test_create_openai_model_uses_the_api_key() -> None:
    model = create_openai_model("gpt-test", api_key="sk-test")

    pydantic_model = model._model
    assert type(pydantic_model) is OpenAIResponsesModel
    assert pydantic_model.model_name == "gpt-test"
    assert pydantic_model.client.api_key == "sk-test"


def test_create_codex_model_uses_the_codex_provider() -> None:
    provider = object()
    with (
        patch("llm.responses.OpenAICodexProvider", return_value=provider),
        patch("llm.responses.OpenAICodexModel") as model_type,
    ):
        create_codex_model("gpt-test", reasoning_effort=ReasoningEffort.HIGH)

    model_type.assert_called_once_with("gpt-test", provider=provider)


async def test_call_maps_the_response_and_sends_tools() -> None:
    pydantic_model = SimpleNamespace(
        request=AsyncMock(
            return_value=PydanticResponse(
                parts=[
                    TextPart("Answer"),
                    ToolCallPart("lookup", '{"key":"value"}', "call-1"),
                ],
                usage=RequestUsage(
                    input_tokens=12, output_tokens=3, cache_read_tokens=8
                ),
                finish_reason="tool_call",
            )
        )
    )
    model = _model(pydantic_model, reasoning_effort=ReasoningEffort.LOW)

    response = await model.call(
        [UserMessage(content="Question")],
        tools=[ModelTool(name="lookup", description="Look it up", parameters={})],
    )

    assert response.completion == "Answer"
    assert response.finish_reason == "tool_call"
    assert response.tool_calls == (
        ToolCall(id="call-1", name="lookup", arguments='{"key":"value"}'),
    )
    assert response.usage == Usage(
        input_tokens=12, output_tokens=3, cache_read_tokens=8
    )
    _, settings, parameters = pydantic_model.request.await_args.args
    assert settings["openai_reasoning_effort"] == "low"
    assert [tool.name for tool in parameters.function_tools] == ["lookup"]
    assert parameters.output_mode == "text"


async def test_call_with_output_type_requests_native_structured_output() -> None:
    pydantic_model = SimpleNamespace(
        request=AsyncMock(
            return_value=PydanticResponse(parts=[TextPart('{"verdict": "ok"}')])
        )
    )
    model = _model(pydantic_model)

    critique = await model.call([UserMessage(content="Review")], output_type=_Critique)

    assert critique == _Critique(verdict="ok")
    parameters = pydantic_model.request.await_args.args[2]
    assert parameters.output_mode == "native"
    assert parameters.output_object.name == "_Critique"
    assert parameters.output_object.json_schema == _Critique.model_json_schema()


async def test_stream_yields_text_deltas_then_the_final_response() -> None:
    final = PydanticResponse(parts=[TextPart("Hello world")])
    streamed = _StreamedResponse(
        [
            PartStartEvent(index=0, part=TextPart("Hello")),
            PartDeltaEvent(index=0, delta=TextPartDelta(" world")),
        ],
        final,
    )
    model = _model(SimpleNamespace(request_stream=_stream_returning(streamed)))

    events = [event async for event in model.stream([UserMessage(content="Hi")])]

    assert events[:2] == [TextDelta(delta="Hello"), TextDelta(delta=" world")]
    assert isinstance(events[2], ModelResponse)
    assert events[2].completion == "Hello world"
    assert events[2].provider_state is final


async def test_context_length_error_is_translated() -> None:
    error = ModelHTTPError(
        status_code=400,
        model_name="gpt-test",
        body={"code": "context_length_exceeded", "message": "Too long"},
    )
    model = _model(SimpleNamespace(request=AsyncMock(side_effect=error)))

    with pytest.raises(ContextLengthExceededError):
        await model.call([UserMessage(content="Question")])


async def test_other_provider_errors_become_model_errors() -> None:
    error = ModelHTTPError(status_code=500, model_name="gpt-test", body=None)
    model = _model(SimpleNamespace(request_stream=_stream_raising(error)))

    with pytest.raises(ModelError) as raised:
        _ = [event async for event in model.stream([UserMessage(content="Hi")])]

    assert not isinstance(raised.value, ContextLengthExceededError)


def test_messages_are_mapped_to_pydantic_ai_requests_and_responses() -> None:
    messages = _pydantic_messages(
        [
            SystemMessage(content="System"),
            UserMessage(
                content="Look",
                images=(Image(data=b"png", media_type="image/png"),),
            ),
            AssistantMessage(
                content="",
                tool_calls=(ToolCall(id="call-1", name="lookup", arguments="{}"),),
            ),
            ToolResultMessage(
                tool_call_id="call-1",
                tool_name="lookup",
                content="Failed",
                is_error=True,
            ),
        ]
    )

    user, assistant, tool_result = messages
    assert isinstance(user, ModelRequest)
    assert user.instructions == "System"
    prompt = user.parts[0]
    assert isinstance(prompt, UserPromptPart)
    assert prompt.content == [
        "Look",
        BinaryContent(data=b"png", media_type="image/png"),
    ]
    assert isinstance(assistant, PydanticResponse)
    assert assistant.parts == [ToolCallPart("lookup", "{}", "call-1")]
    assert isinstance(tool_result, ModelRequest)
    tool_return = tool_result.parts[0]
    assert isinstance(tool_return, ToolReturnPart)
    assert tool_return.tool_call_id == "call-1"
    assert tool_return.outcome == "failed"


def test_provider_state_is_replayed_for_follow_up_requests() -> None:
    state = PydanticResponse(parts=[TextPart("partial")])

    assert _pydantic_messages(
        [AssistantMessage(content="partial", provider_state=state)]
    ) == [state]


def _model(
    pydantic_model: object,
    *,
    reasoning_effort: ReasoningEffort | None = None,
) -> ResponsesChatModel:
    return ResponsesChatModel(
        cast(OpenAIResponsesModel, pydantic_model),
        reasoning_effort=reasoning_effort,
    )


class _StreamedResponse:
    def __init__(self, events: list[Any], final: PydanticResponse) -> None:
        self._events = events
        self._final = final

    async def __aiter__(self):
        for event in self._events:
            yield event

    def get(self) -> PydanticResponse:
        return self._final


def _stream_returning(streamed: _StreamedResponse):
    @asynccontextmanager
    async def request_stream(*args: object):
        yield streamed

    return request_stream


def _stream_raising(error: Exception):
    @asynccontextmanager
    async def request_stream(*args: object):
        raise error
        yield

    return request_stream
