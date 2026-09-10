from backend.presentation.feature import api_feature

from .infrastructure.di import UserProvider
from .presentation import user_router

feature = api_feature(
    name="user",
    routers=[user_router],
    providers=[UserProvider],
)

__all__ = ["feature"]
