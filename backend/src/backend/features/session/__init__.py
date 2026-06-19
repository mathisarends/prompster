from backend.presentation.feature import Feature

from .infrastructure.di import SessionProvider
from .presentation import (
    image_attachment_router,
    register_session_exception_handlers,
    router,
    session_schema_router,
)

feature = Feature(
    name="session",
    routers=[router, image_attachment_router, session_schema_router],
    providers=[SessionProvider],
    register_exception_handlers=register_session_exception_handlers,
)

__all__ = ["feature"]
