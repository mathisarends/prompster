from backend.presentation.feature import api_feature

from .infrastructure.di import SessionProvider
from .presentation import (
    image_attachment_router,
    router,
    session_schema_router,
)

feature = api_feature(
    name="session",
    routers=[router, image_attachment_router, session_schema_router],
    providers=[SessionProvider],
)

__all__ = ["feature"]
