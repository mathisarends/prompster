from backend.presentation.feature import api_feature

from .presentation import router

feature = api_feature(
    routers=[router],
)

__all__ = ["feature"]
