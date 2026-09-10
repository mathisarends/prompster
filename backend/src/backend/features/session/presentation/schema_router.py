from backend.features.auth.presentation.dependencies import AuthenticatedUserId
from backend.features.auth.presentation.exceptions import (
    AUTHENTICATION_REQUIRED_ERROR,
)
from backend.features.session.presentation.exceptions import SESSION_ERRORS
from backend.features.session.presentation.schemas import EntryKindSchema
from backend.features.session.presentation.sse import (
    SessionEventTypeSchema,
    SessionServerEvent,
    SpotifyExportServerEventSchema,
)
from dishka.integrations.fastapi import DishkaRoute
from fastapi import status
from fastapi_canon import CanonRouter

session_schema_router = CanonRouter(
    route_class=DishkaRoute,
    prefix="/sessions",
    tags=["session_schemas"],
    error_registry=SESSION_ERRORS,
    raises=(AUTHENTICATION_REQUIRED_ERROR,),
)


@session_schema_router.get(
    "/events/schema",
    response_model=SessionServerEvent,
    status_code=status.HTTP_200_OK,
    operation_id="get_session_event_schema",
)
async def get_session_event_schema(
    _authenticated_user_id: AuthenticatedUserId,
) -> SessionServerEvent:
    return SessionServerEvent(None)


@session_schema_router.get(
    "/playlist/spotify/events/schema",
    response_model=SpotifyExportServerEventSchema,
    status_code=status.HTTP_200_OK,
    operation_id="get_spotify_export_event_schema",
)
async def get_spotify_export_event_schema(
    _authenticated_user_id: AuthenticatedUserId,
) -> SpotifyExportServerEventSchema:
    return SpotifyExportServerEventSchema(None)


@session_schema_router.get(
    "/events/type/schema",
    response_model=SessionEventTypeSchema,
    status_code=status.HTTP_200_OK,
    operation_id="get_session_event_type_schema",
)
async def get_session_event_type_schema(
    _authenticated_user_id: AuthenticatedUserId,
) -> SessionEventTypeSchema:
    return SessionEventTypeSchema("done")


@session_schema_router.get(
    "/entries/kind/schema",
    response_model=EntryKindSchema,
    status_code=status.HTTP_200_OK,
    operation_id="get_session_entry_kind_schema",
)
async def get_session_entry_kind_schema(
    _authenticated_user_id: AuthenticatedUserId,
) -> EntryKindSchema:
    return EntryKindSchema("user_message")
