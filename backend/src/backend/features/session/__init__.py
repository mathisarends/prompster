from backend.presentation.feature import Feature

from .infrastructure.di import SessionProvider
from .presentation import register_session_exception_handlers, router

feature = Feature(
    name="session",
    routers=[router],
    providers=[SessionProvider],
    register_exception_handlers=register_session_exception_handlers,
)

__all__ = ["feature"]
