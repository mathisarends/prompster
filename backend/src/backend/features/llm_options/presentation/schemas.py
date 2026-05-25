from llm import LLMProvider

from backend.presentation.schema import Schema


class LLMOptionResponse(Schema):
    id: str
    provider: LLMProvider
    label: str
    is_default: bool


class LLMOptionsResponse(Schema):
    items: list[LLMOptionResponse]
