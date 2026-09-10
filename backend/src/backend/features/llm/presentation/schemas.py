from backend.features.llm.configuration import LLMProvider, ReasoningEffort
from backend.presentation.schema import Schema


class LLMCapabilitiesResponse(Schema):
    temperature: bool
    reasoning_effort: list[ReasoningEffort]


class LLMDefaultsResponse(Schema):
    reasoning_effort: ReasoningEffort | None


class LLMOptionResponse(Schema):
    id: str
    provider: LLMProvider
    label: str
    profile: str
    capabilities: LLMCapabilitiesResponse
    defaults: LLMDefaultsResponse
    is_default: bool


class LLMOptionsResponse(Schema):
    items: list[LLMOptionResponse]
