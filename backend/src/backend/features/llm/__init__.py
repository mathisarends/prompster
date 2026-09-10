from backend.presentation.feature import api_feature

from .infrastructure import LLMFeatureProvider
from .presentation import router

feature = api_feature(
    routers=[router],
    providers=[LLMFeatureProvider],
)

__all__ = ["feature"]
