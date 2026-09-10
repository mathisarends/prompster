from backend.presentation.feature import api_feature

from .infrastructure.di import AuthProvider
from .presentation import AUTH_ERRORS, auth_router

feature = api_feature(
    name="auth",
    routers=[auth_router],
    providers=[AuthProvider],
    errors=AUTH_ERRORS,
)

__all__ = ["feature"]
