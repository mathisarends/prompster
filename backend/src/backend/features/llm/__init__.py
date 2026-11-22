from fastapi_canon import Feature

from .infrastructure import LLMFeatureProvider
from .presentation import router

feature = Feature(
    name="llm",
    routers=[router],
    providers=[LLMFeatureProvider],
)

__all__ = ["feature"]
