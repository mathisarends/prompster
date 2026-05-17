from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Response, status
from fastapi.responses import StreamingResponse

from backend.features.auth.presentation.dependencies import AuthenticatedUserId
from backend.features.session.application import (
    CreateSessionHandler,
    DeleteSessionHandler,
    GetSessionByIdHandler,
    SendMessageHandler,
    UpdateSessionHandler,
)
from backend.features.session.presentation.dependencies import AuthorizedSession
from backend.features.session.presentation.mapper import to_session_response
from backend.features.session.presentation.schemas import (
    ErrorResponse,
    SendMessageRequest,
    SessionCreateRequest,
    SessionResponse,
    SessionUpdateRequest,
)

router = APIRouter(route_class=DishkaRoute, prefix="/sessions", tags=["sessions"])

_auth_error_responses = {
    status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse},
    status.HTTP_403_FORBIDDEN: {"model": ErrorResponse},
}


@router.get(
    "/{session_id}",
    response_model=SessionResponse,
    status_code=status.HTTP_200_OK,
    operation_id="get_session",
    responses={
        status.HTTP_401_UNAUTHORIZED: _auth_error_responses[
            status.HTTP_401_UNAUTHORIZED
        ],
        status.HTTP_403_FORBIDDEN: _auth_error_responses[status.HTTP_403_FORBIDDEN],
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
    },
)
async def get_session_by_id(
    session: AuthorizedSession,
    handler: FromDishka[GetSessionByIdHandler],
) -> SessionResponse:
    session = await handler.handle(session=session)
    return to_session_response(session)


@router.post(
    "",
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="create_session",
    responses={
        status.HTTP_401_UNAUTHORIZED: _auth_error_responses[
            status.HTTP_401_UNAUTHORIZED
        ]
    },
)
async def create_session(
    authenticated_user_id: AuthenticatedUserId,
    body: SessionCreateRequest,
    handler: FromDishka[CreateSessionHandler],
) -> SessionResponse:
    session = await handler.handle(
        owner_id=authenticated_user_id,
        initial_prompt=body.initial_prompt,
    )
    return to_session_response(session)


@router.post(
    "/{session_id}/messages",
    status_code=status.HTTP_201_CREATED,
    operation_id="send_message",
    responses={
        status.HTTP_201_CREATED: {"content": {"text/plain": {}}},
        status.HTTP_401_UNAUTHORIZED: _auth_error_responses[
            status.HTTP_401_UNAUTHORIZED
        ],
        status.HTTP_403_FORBIDDEN: _auth_error_responses[status.HTTP_403_FORBIDDEN],
        status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse},
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
    },
)
async def send_message(
    session: AuthorizedSession,
    body: SendMessageRequest,
    handler: FromDishka[SendMessageHandler],
) -> StreamingResponse:
    return StreamingResponse(
        handler.stream_response(session=session, content=body.content),
        media_type="text/plain; charset=utf-8",
    )


@router.patch(
    "/{session_id}",
    response_model=SessionResponse,
    status_code=status.HTTP_200_OK,
    operation_id="update_session",
    responses={
        status.HTTP_401_UNAUTHORIZED: _auth_error_responses[
            status.HTTP_401_UNAUTHORIZED
        ],
        status.HTTP_403_FORBIDDEN: _auth_error_responses[status.HTTP_403_FORBIDDEN],
        status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse},
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
    },
)
async def update_session(
    session: AuthorizedSession,
    body: SessionUpdateRequest,
    handler: FromDishka[UpdateSessionHandler],
) -> SessionResponse:
    session = await handler.handle(
        session=session,
        title=body.title,
    )
    return to_session_response(session)


@router.delete(
    "/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="delete_session",
    responses={
        status.HTTP_401_UNAUTHORIZED: _auth_error_responses[
            status.HTTP_401_UNAUTHORIZED
        ],
        status.HTTP_403_FORBIDDEN: _auth_error_responses[status.HTTP_403_FORBIDDEN],
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
    },
)
async def delete_session(
    session: AuthorizedSession,
    handler: FromDishka[DeleteSessionHandler],
) -> Response:
    await handler.handle(session=session)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
