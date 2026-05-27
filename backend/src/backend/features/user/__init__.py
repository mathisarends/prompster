from backend.presentation.feature import Feature

from .infrastructure.di import UserProvider
from .presentation import register_user_exception_handlers, user_router

feature = Feature(
    name="user",
    routers=[user_router],
    providers=[UserProvider],
    register_exception_handlers=register_user_exception_handlers,
)

__all__ = ["feature"]
