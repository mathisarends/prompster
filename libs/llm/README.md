## llm package

Provider-neutral message, tool, streaming-event, and `ChatModel` ports for the
workspace, replacing `py-llmify`.

`ResponsesChatModel` implements the port over Pydantic AI's OpenAI Responses
model via HTTP. Two factories pick the authentication:

- `create_openai_model(model_name, api_key=...)` uses an OpenAI API key.
- `create_codex_model(model_name)` reuses the ChatGPT subscription login of the
  local Codex CLI (`codex login`).

```python
llm = create_openai_model("gpt-5.5", api_key=key)

response = await llm.call([SystemMessage(content="..."), UserMessage(content="Hi")])
critique = await llm.call(messages, output_type=DeckCritique)  # -> DeckCritique

async for event in llm.stream(messages, tools=tools):
    ...  # TextDelta events, then exactly one ModelResponse
```

A request that no longer fits the context window raises
`ContextLengthExceededError`; other provider failures raise `ModelError`.
