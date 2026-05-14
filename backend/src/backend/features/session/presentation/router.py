from uuid import UUID

from dishka.integrations.fastapi import DishkaRoute, FromDishka, inject
from fastapi import APIRouter, Response, status

from backend.features.session.application import (
    CreateSessionHandler,
    DeleteSessionHandler,
    GetSessionByIdHandler,
    UpdateSessionHandler,
)
from backend.features.session.presentation.mapper import to_session_response
from backend.features.session.presentation.schemas import (
    ErrorResponse,
    SessionCreateRequest,
    SessionResponse,
    SessionUpdateRequest,
)

router = APIRouter(route_class=DishkaRoute, prefix="/sessions", tags=["sessions"])


@router.get(
    "/{session_id}",
    response_model=SessionResponse,
    status_code=status.HTTP_200_OK,
    operation_id="get_session",
    summary="Get a single session by ID",
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}},
)
@inject
async def get_session_by_id(
    session_id: UUID,
    handler: FromDishka[GetSessionByIdHandler],
) -> SessionResponse:
    session = await handler.handle(session_id=session_id)
    return to_session_response(session)


@router.post(
    "",
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="create_session",
    summary="Create a new session",
)
@inject
async def create_session(
    body: SessionCreateRequest,
    handler: FromDishka[CreateSessionHandler],
) -> SessionResponse:
    session = await handler.handle(title=body.title, system_prompt=body.system_prompt)
    return to_session_response(session)


@router.patch(
    "/{session_id}",
    response_model=SessionResponse,
    status_code=status.HTTP_200_OK,
    operation_id="update_session",
    summary="Update an existing session",
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse},
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
    },
)
@inject
async def update_session(
    session_id: UUID,
    body: SessionUpdateRequest,
    handler: FromDishka[UpdateSessionHandler],
) -> SessionResponse:
    session = await handler.handle(
        session_id=session_id,
        title=body.title,
        system_prompt=body.system_prompt,
    )
    return to_session_response(session)


@router.delete(
    "/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="delete_session",
    summary="Delete a session",
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}},
)
@inject
async def delete_session(
    session_id: UUID,
    handler: FromDishka[DeleteSessionHandler],
) -> Response:
    await handler.handle(session_id=session_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
