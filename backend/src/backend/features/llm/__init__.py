from fastapi_canon import Feature

from backend.features.llm.infrastructure import LLMFeatureProvider
from backend.features.llm.presentation import router

feature = Feature(
    name="llm",
    routers=[router],
    providers=[LLMFeatureProvider],
)

__all__ = ["feature"]
