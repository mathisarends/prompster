from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, status

from backend.features.auth.presentation.dependencies import AuthenticatedUserId
from backend.features.session.presentation.schemas import EntryKindSchema, ErrorResponse
from backend.features.session.presentation.sse import (
    SessionEventTypeSchema,
    SessionServerEvent,
    SpotifyExportServerEventSchema,
)

session_schema_router = APIRouter(
    route_class=DishkaRoute,
    prefix="/sessions",
    tags=["session_schemas"],
)

_auth_errors = {
    status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse},
    status.HTTP_403_FORBIDDEN: {"model": ErrorResponse},
}


@session_schema_router.get(
    "/events/schema",
    response_model=SessionServerEvent,
    status_code=status.HTTP_200_OK,
    operation_id="get_session_event_schema",
    responses=_auth_errors,
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
    responses=_auth_errors,
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
    responses=_auth_errors,
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
    responses=_auth_errors,
)
async def get_session_entry_kind_schema(
    _authenticated_user_id: AuthenticatedUserId,
) -> EntryKindSchema:
    return EntryKindSchema("user_message")
