from backend.presentation.feature import api_feature

from .infrastructure.di import AuthProvider
from .presentation import auth_router

feature = api_feature(
    name="auth",
    routers=[auth_router],
    providers=[AuthProvider],
)

__all__ = ["feature"]
