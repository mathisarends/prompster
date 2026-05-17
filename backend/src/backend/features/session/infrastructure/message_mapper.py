import json

from backend.features.session.domain import (
    MessageRole,
    SessionMessage,
    ToolCall,
    ToolCallState,
)


def to_openai_messages(messages: list[SessionMessage]) -> list[dict]:
    result: list[dict] = []
    for message in messages:
        result.extend(_map_message(message))
    return result


def _map_message(message: SessionMessage) -> list[dict]:
    if message.role == MessageRole.USER:
        return [{"role": "user", "content": message.content}]

    assistant: dict = {"role": "assistant", "content": message.content}
    group = message.tool_call_group
    if group is None:
        return [assistant]

    assistant["tool_calls"] = [_map_tool_call(call) for call in group.calls]
    tool_messages = [_map_tool_result(call) for call in group.calls if call.is_resolved]
    return [assistant, *tool_messages]


def _map_tool_call(call: ToolCall) -> dict:
    return {
        "id": call.id,
        "type": "function",
        "function": {
            "name": call.function.name,
            "arguments": json.dumps(call.function.arguments),
        },
    }


def _map_tool_result(call: ToolCall) -> dict:
    content = call.error if call.state == ToolCallState.FAILED else call.result
    return {
        "role": "tool",
        "tool_call_id": call.id,
        "content": content or "",
    }
