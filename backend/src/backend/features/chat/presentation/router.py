from uuid import UUID

from dishka.integrations.fastapi import DishkaRoute, FromDishka, inject
from fastapi import APIRouter, Response, status

from backend.features.chat.application import (
    CreateChatHandler,
    DeleteChatHandler,
    GetChatByIdHandler,
    UpdateChatHandler,
)
from backend.features.chat.presentation.mapper import to_chat_response
from backend.features.chat.presentation.schemas import (
    ChatCreateRequest,
    ChatResponse,
    ChatUpdateRequest,
    ErrorResponse,
)

router = APIRouter(route_class=DishkaRoute, prefix="/chats", tags=["chats"])


@router.get(
    "/{chat_id}",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    operation_id="get_chat",
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}},
)
async def get_chat_by_id(
    chat_id: UUID,
    handler: FromDishka[GetChatByIdHandler],
) -> ChatResponse:
    chat = await handler.handle(chat_id=chat_id)
    return to_chat_response(chat)


@router.post(
    "",
    response_model=ChatResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="create_chat",
)
async def create_chat(
    handler: FromDishka[CreateChatHandler],
) -> ChatResponse:
    chat = await handler.handle(title=body.title, system_prompt=body.system_prompt)
    return to_chat_response(chat)


@router.patch(
    "/{chat_id}",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    operation_id="update_chat",
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse},
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
    },
)
async def update_chat(
    chat_id: UUID,
    body: ChatUpdateRequest,
    handler: FromDishka[UpdateChatHandler],
) -> ChatResponse:
    chat = await handler.handle(
        chat_id=chat_id,
        title=body.title,
        system_prompt=body.system_prompt,
    )
    return to_chat_response(chat)


@router.delete(
    "/{chat_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="delete_chat",
    summary="Delete a chat",
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}},
)
async def delete_chat(
    chat_id: UUID,
    handler: FromDishka[DeleteChatHandler],
) -> Response:
    await handler.handle(chat_id=chat_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
