from uuid import UUID

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, HTTPException, Response, status

from backend.features.chat.application import (
	ChatNotFoundApplicationError,
	ChatUpdateValidationError,
	CreateChatHandler,
	DeleteChatHandler,
	GetChatByIdHandler,
	UpdateChatHandler,
)
from backend.features.chat.presentation.mapper import to_chat_response_schema
from backend.features.chat.presentation.schemas import (
	ChatCreateRequestSchema,
	ChatResponseSchema,
	ChatUpdateRequestSchema,
)

router = APIRouter(route_class=DishkaRoute, prefix="/chats", tags=["chats"])


@router.get("/{chat_id}", response_model=ChatResponseSchema)
async def get_chat_by_id(
	chat_id: UUID,
	handler: FromDishka[GetChatByIdHandler],
) -> ChatResponseSchema:
	try:
		chat = await handler.handle(chat_id=chat_id)
	except ChatNotFoundApplicationError as exc:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found") from exc

	return to_chat_response_schema(chat)


@router.post("/", response_model=ChatResponseSchema, status_code=status.HTTP_201_CREATED)
async def create_chat(
	body: ChatCreateRequestSchema,
	handler: FromDishka[CreateChatHandler],
) -> ChatResponseSchema:
	chat = await handler.handle(title=body.title, system_prompt=body.system_prompt)
	return to_chat_response_schema(chat)


@router.patch("/{chat_id}", response_model=ChatResponseSchema)
async def update_chat(
	chat_id: UUID,
	body: ChatUpdateRequestSchema,
	handler: FromDishka[UpdateChatHandler],
) -> ChatResponseSchema:
	try:
		chat = await handler.handle(
			chat_id=chat_id,
			title=body.title,
			system_prompt=body.system_prompt,
		)
	except ChatUpdateValidationError as exc:
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
	except ChatNotFoundApplicationError as exc:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found") from exc

	return to_chat_response_schema(chat)


@router.delete("/{chat_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chat(
	chat_id: UUID,
	handler: FromDishka[DeleteChatHandler],
) -> Response:
	try:
		await handler.handle(chat_id=chat_id)
	except ChatNotFoundApplicationError as exc:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found") from exc

	return Response(status_code=status.HTTP_204_NO_CONTENT)

