from backend.features.auth.presentation.dependencies import AuthenticatedUserId
from backend.features.auth.presentation.exceptions import (
    AUTHENTICATION_REQUIRED_ERROR,
)
from backend.features.session.presentation.schemas import EntryKindSchema
from fastapi import status
from fastapi_canon import APIRouter

session_schema_router = APIRouter(
    prefix="/sessions",
    tags=["session_schemas"],
    raises=(AUTHENTICATION_REQUIRED_ERROR,),
)


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
