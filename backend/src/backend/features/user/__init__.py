from backend.presentation.feature import api_feature

from .infrastructure.di import UserProvider
from .presentation import USER_ERRORS, user_router

feature = api_feature(
    routers=[user_router],
    providers=[UserProvider],
    errors=USER_ERRORS,
)

__all__ = ["feature"]
