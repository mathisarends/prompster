---
name: llmify
description: >
  How to use the py-llmify library for LLM chat completions in Python.
  Use this skill whenever the user writes code with py-llmify / llmify, asks how to call OpenAI, Anthropic, or Azure OpenAI via llmify, wants to do structured outputs, tool calling, streaming, or image analysis with llmify, or gets stuck on imports/API surface. Also trigger when the user mentions ChatOpenAI, ChatAnthropic, ChatAzureOpenAI, UserMessage, SystemMessage, @tool, RawSchemaTool, or ChatInvokeCompletion.
---

# py-llmify Usage Skill

Thin, async-first wrapper around OpenAI, Azure OpenAI, and Anthropic SDKs.
Pip package: `py-llmify` — import root is `llmify`.

## Installation

```bash
pip install py-llmify[openai]      # OpenAI + Azure
pip install py-llmify[anthropic]   # Anthropic / Claude
pip install py-llmify[all]         # All providers
```

## Environment Variables

```bash
OPENAI_API_KEY="sk-..."
AZURE_OPENAI_API_KEY="..."
AZURE_OPENAI_ENDPOINT="https://<resource>.openai.azure.com/"
ANTHROPIC_API_KEY="sk-ant-..."
```

---

## Client Instantiation

```python
from llmify import ChatOpenAI, ChatAzureOpenAI, ChatAnthropic

llm = ChatOpenAI(model="gpt-4o")
llm = ChatAzureOpenAI(model="gpt-4o")
llm = ChatAnthropic(model="claude-sonnet-4-20250514")
```

Constructor kwargs (all optional, can also be overridden per `invoke`/`stream` call):
`temperature`, `max_tokens`, `top_p`, `frequency_penalty`, `presence_penalty`, `stop`, `seed`

---

## Message Types

```python
from llmify import SystemMessage, UserMessage, AssistantMessage, ToolResultMessage
```

| Class                                              | When to use                                     |
| -------------------------------------------------- | ----------------------------------------------- |
| `SystemMessage(content=...)`                       | System / persona prompt                         |
| `UserMessage(content=...)`                         | User turn (text or list of content parts)       |
| `AssistantMessage(content=..., tool_calls=...)`    | Model turn, include when replaying tool results |
| `ToolResultMessage(tool_call_id=..., content=...)` | Result of a tool call                           |

---

## Basic `invoke`

```python
response = await llm.invoke([
    SystemMessage(content="You are a helpful assistant"),
    UserMessage(content="What is 2+2?"),
])
print(response.completion)   # str
```

`ChatInvokeCompletion` fields:

- `completion` — `str` or parsed Pydantic model (when `output_format` is set)
- `tool_calls` — `list[ToolCall]` (empty list if none)
- `usage` — `ChatInvokeUsage` (prompt/completion token counts)
- `stop_reason` — why the model stopped

---

## Structured Output

```python
from pydantic import BaseModel
from llmify import ChatOpenAI, UserMessage

class Person(BaseModel):
    name: str
    age: int

response = await llm.invoke(
    [UserMessage(content="Extract: Alice is 30 years old")],
    output_format=Person,
)
person: Person = response.completion
```

---

## Tool Calling

### `@tool` decorator (recommended)

```python
from llmify import tool, AssistantMessage, ToolResultMessage
import json

@tool
def get_weather(location: str, unit: str = "celsius") -> str:
    """Get current weather for a location."""
    return f"22°C, Sunny in {location}"

messages = [UserMessage(content="Weather in Berlin?")]
response = await llm.invoke(messages, tools=[get_weather])

if response.tool_calls:
    tc = response.tool_calls[0]
    result = get_weather(**json.loads(tc.function.arguments))
    messages += [
        AssistantMessage(content=response.completion, tool_calls=response.tool_calls),
        ToolResultMessage(tool_call_id=tc.id, content=result),
    ]
    final = await llm.invoke(messages, tools=[get_weather])
    print(final.completion)
```

### `RawSchemaTool` (full schema control)

```python
from llmify import RawSchemaTool

tool = RawSchemaTool(
    name="search_web",
    description="Search the web",
    schema={
        "type": "object",
        "properties": {"query": {"type": "string"}},
        "required": ["query"],
    },
)
response = await llm.invoke(messages, tools=[tool])
```

### Raw OpenAI-style dict

```python
tools = [{"type": "function", "function": {"name": "...", "description": "...", "parameters": {...}}}]
response = await llm.invoke(messages, tools=tools)
```

---

## Streaming

```python
async for chunk in llm.stream([UserMessage(content="Write a haiku")]):
    print(chunk, end="", flush=True)
```

---

## Image Input

Use content parts inside `UserMessage`:

```python
from llmify import UserMessage, ContentPartTextParam, ContentPartImageParam, ImageURL

msg = UserMessage(content=[
    ContentPartTextParam(text="What's in this image?"),
    ContentPartImageParam(
        image_url=ImageURL(
            url="data:image/jpeg;base64,<base64data>",
            media_type="image/jpeg",
            detail="high",  # "low" | "high" | "auto"
        )
    ),
])
response = await llm.invoke([msg])
```

---

## Common Patterns

### Multi-turn conversation

```python
history = [SystemMessage(content="You are a Python expert")]

async def chat(user_input: str) -> str:
    history.append(UserMessage(content=user_input))
    response = await llm.invoke(history)
    history.append(AssistantMessage(content=response.completion))
    return response.completion
```

### Agentic tool loop

```python
while True:
    response = await llm.invoke(messages, tools=tools)
    if not response.tool_calls:
        break
    messages.append(AssistantMessage(content=response.completion, tool_calls=response.tool_calls))
    for tc in response.tool_calls:
        result = dispatch_tool(tc)
        messages.append(ToolResultMessage(tool_call_id=tc.id, content=result))
print(response.completion)
```

---

## Key Notes

- All `invoke` and `stream` calls are **async** — always use `await` / `async for`
- `tool_calls` is always a list (never `None`); check `if response.tool_calls:`
- When replaying tool results, always include the `AssistantMessage` with `tool_calls=` **before** the `ToolResultMessage`
- `@tool` reads the function's docstring as the tool description — keep it concise and accurate
- All three providers expose the same `invoke` / `stream` / structured output / tool calling surface
