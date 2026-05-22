import json

from backend.features.session.domain import (
    AssistantMessage,
    CompletedCall,
    FailedCall,
    PendingCall,
    SessionEntry,
    ToolCall,
    ToolCallSequence,
    UserMessage,
)


def to_openai_messages(entries: list[SessionEntry]) -> list[dict]:
    result: list[dict] = []
    for entry in entries:
        if isinstance(entry, UserMessage):
            result.append({"role": "user", "content": entry.content})
        elif isinstance(entry, AssistantMessage):
            result.append({"role": "assistant", "content": entry.content})
        elif isinstance(entry, ToolCallSequence):
            result.extend(_map_tool_call_sequence(entry))
    return result


def _map_tool_call_sequence(sequence: ToolCallSequence) -> list[dict]:
    messages: list[dict] = []
    for call in sequence.calls:
        messages.append(
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [_map_tool_call(call)],
            }
        )
        if not isinstance(call, PendingCall):
            messages.append(_map_tool_result(call))
    return messages


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
    if isinstance(call, CompletedCall):
        content = call.result
    elif isinstance(call, FailedCall):
        content = call.error
    else:
        content = ""
    return {
        "role": "tool",
        "tool_call_id": call.id,
        "content": content,
    }
