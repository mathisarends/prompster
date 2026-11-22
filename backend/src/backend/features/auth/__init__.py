from fastapi_canon import Feature

from .infrastructure.di import AuthProvider
from .presentation import AUTH_ERRORS, auth_router

feature = Feature(
    name="auth",
    routers=[auth_router],
    errors=AUTH_ERRORS,
    providers=[AuthProvider],
)

__all__ = ["feature"]
