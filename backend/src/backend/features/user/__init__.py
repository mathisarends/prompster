from fastapi_canon import Feature

from backend.features.user.infrastructure.di import UserProvider
from backend.features.user.presentation import user_router

feature = Feature(
    name="user",
    routers=[user_router],
    providers=[UserProvider],
)

__all__ = ["feature"]
