from uuid import UUID

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Response, status

from backend.features.session.application import (
    CreateSessionHandler,
    DeleteSessionHandler,
    GetSessionByIdHandler,
    SendMessageHandler,
    UpdateSessionHandler,
)
from backend.features.session.presentation.mapper import (
    to_message_response,
    to_session_response,
)
from backend.features.session.presentation.schemas import (
    ErrorResponse,
    MessageResponse,
    SendMessageRequest,
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
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}},
)
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
)
async def create_session(
    body: SessionCreateRequest,
    handler: FromDishka[CreateSessionHandler],
) -> SessionResponse:
    session = await handler.handle(
        initial_prompt=body.initial_prompt,
        system_prompt=body.system_prompt,
    )
    return to_session_response(session)


@router.post(
    "/{session_id}/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="send_message",
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse},
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
    },
)
async def send_message(
    session_id: UUID,
    body: SendMessageRequest,
    handler: FromDishka[SendMessageHandler],
) -> MessageResponse:
    message = await handler.handle(session_id=session_id, content=body.content)
    return to_message_response(message)


@router.patch(
    "/{session_id}",
    response_model=SessionResponse,
    status_code=status.HTTP_200_OK,
    operation_id="update_session",
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse},
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
    },
)
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
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}},
)
async def delete_session(
    session_id: UUID,
    handler: FromDishka[DeleteSessionHandler],
) -> Response:
    await handler.handle(session_id=session_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
