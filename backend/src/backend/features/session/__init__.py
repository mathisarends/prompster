from backend.presentation.feature import api_feature

from .infrastructure.di import SessionProvider
from .presentation import (
    SESSION_ERRORS,
    image_attachment_router,
    router,
    session_schema_router,
)

feature = api_feature(
    routers=[router, image_attachment_router, session_schema_router],
    providers=[SessionProvider],
    errors=SESSION_ERRORS,
)

__all__ = ["feature"]
