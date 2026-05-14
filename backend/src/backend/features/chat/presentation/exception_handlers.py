from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from backend.features.chat.application.exceptions import (
    ChatNotFoundApplicationError,
    ChatUpdateValidationError,
)
from backend.features.chat.domain.exceptions import ChatNotFoundError


def _exception_detail(exc: Exception, *, fallback: str) -> str:
    detail = str(exc).strip()
    return detail if detail else fallback


async def _chat_not_found_handler(
    _: Request,
    exc: ChatNotFoundApplicationError | ChatNotFoundError,
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": _exception_detail(exc, fallback="Chat not found")},
    )


async def _chat_validation_handler(
    _: Request, exc: ChatUpdateValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "detail": _exception_detail(exc, fallback="Invalid chat update payload")
        },
    )


def register_chat_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ChatNotFoundApplicationError, _chat_not_found_handler)
    app.add_exception_handler(ChatNotFoundError, _chat_not_found_handler)
    app.add_exception_handler(ChatUpdateValidationError, _chat_validation_handler)
