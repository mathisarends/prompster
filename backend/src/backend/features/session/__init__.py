from fastapi_canon import Feature

from backend.features.session.infrastructure.di import SessionProvider
from backend.features.session.presentation import (
    SESSION_ERRORS,
    image_attachment_router,
    router,
    rpc_router,
    session_schema_router,
)

feature = Feature(
    name="session",
    routers=[router, image_attachment_router, session_schema_router],
    errors=SESSION_ERRORS,
    providers=[SessionProvider],
)

__all__ = ["feature", "rpc_router"]
