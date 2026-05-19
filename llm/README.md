## llm package

Thin central factory for OpenAI LLMs shared across the workspace.

Encapsulates:

- Allowed models via `OpenAIModelName` enum (`gpt-5.4`, `gpt-5.4-mini`, `gpt-5.5`)
- Credential loading via `pydantic-settings` (`OPENAI_API_KEY`)
- Validation with `ensure_supported_openai_model(model: str) -> OpenAIModelName`
- Factory functions returning a `ChatOpenAI` instance

Both `backend` and `agent` depend on this package so LLM construction and credentials are maintained in one place.

### registry

```python
class OpenAIModelName(StrEnum):
    GPT_5_4       = "gpt-5.4"
    GPT_5_4_MINI  = "gpt-5.4-mini"   # default
    GPT_5_5       = "gpt-5.5"

ensure_supported_openai_model(model: str) -> OpenAIModelName  # raises ValueError if unknown
```

### factory

```python
# Generic — pick any model
create_openai_llm(
    model: OpenAIModelName = DEFAULT_OPENAI_MODEL,
    *,
    api_key: str | None = None,
    credentials: LLMCredentials | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    **kwargs,
) -> ChatOpenAI

# Convenience shorthands (same kwargs, model pre-set)
create_gpt_5_4(...)       # gpt-5.4
create_gpt_5_4_mini(...)  # gpt-5.4-mini
create_gpt_5_5(...)       # gpt-5.5
```

If `api_key` is `None`, the factory falls back to `LLMCredentials().openai_api_key`.
