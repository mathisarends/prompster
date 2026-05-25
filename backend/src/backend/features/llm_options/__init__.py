from backend.presentation.feature import Feature

from .presentation import router

feature = Feature(
    name="llm_options",
    routers=[router],
)

__all__ = ["feature"]
