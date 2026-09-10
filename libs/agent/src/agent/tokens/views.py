from pydantic import BaseModel


class TokenUsageEntry(BaseModel):
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    prompt_cached_tokens: int | None


class UsageSummary(BaseModel):
    total_tokens: int
    total_prompt_tokens: int
    total_completion_tokens: int
    total_prompt_cached_tokens: int
