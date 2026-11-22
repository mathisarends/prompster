from fastapi_canon import Feature

from backend.features.auth.infrastructure.di import AuthProvider
from backend.features.auth.presentation import AUTH_ERRORS, auth_router

feature = Feature(
    name="auth",
    routers=[auth_router],
    errors=AUTH_ERRORS,
    providers=[AuthProvider],
)

__all__ = ["feature"]
