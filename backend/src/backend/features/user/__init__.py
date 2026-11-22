from fastapi_canon import Feature

from .infrastructure.di import UserProvider
from .presentation import user_router

feature = Feature(
    name="user",
    routers=[user_router],
    providers=[UserProvider],
)

__all__ = ["feature"]
