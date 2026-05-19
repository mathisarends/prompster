import json

from backend.features.session.domain import (
    AssistantMessage,
    CompletedCall,
    FailedCall,
    PendingCall,
    SessionEntry,
    ToolCall,
    ToolCallGroup,
    UserMessage,
)


def to_openai_messages(entries: list[SessionEntry]) -> list[dict]:
    result: list[dict] = []
    for entry in entries:
        if isinstance(entry, UserMessage):
            result.append({"role": "user", "content": entry.content})
        elif isinstance(entry, AssistantMessage):
            result.append({"role": "assistant", "content": entry.content})
        elif isinstance(entry, ToolCallGroup):
            result.extend(_map_tool_call_group(entry))
    return result


def _map_tool_call_group(group: ToolCallGroup) -> list[dict]:
    assistant = {
        "role": "assistant",
        "content": "",
        "tool_calls": [_map_tool_call(call) for call in group.calls],
    }
    tool_messages = [
        _map_tool_result(call)
        for call in group.calls
        if not isinstance(call, PendingCall)
    ]
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
