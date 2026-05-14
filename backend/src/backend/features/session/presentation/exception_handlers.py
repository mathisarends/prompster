from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from backend.features.session.application.exceptions import (
    SessionNotFoundApplicationError,
    SessionUpdateValidationError,
)
from backend.features.session.domain.exceptions import SessionNotFoundError


def _exception_detail(exc: Exception, *, fallback: str) -> str:
    detail = str(exc).strip()
    return detail if detail else fallback


async def _session_not_found_handler(
    _: Request,
    exc: SessionNotFoundApplicationError | SessionNotFoundError,
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": _exception_detail(exc, fallback="Session not found")},
    )


async def _session_validation_handler(
    _: Request, exc: SessionUpdateValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "detail": _exception_detail(exc, fallback="Invalid session update payload")
        },
    )


def register_session_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(
        SessionNotFoundApplicationError, _session_not_found_handler
    )
    app.add_exception_handler(SessionNotFoundError, _session_not_found_handler)
    app.add_exception_handler(SessionUpdateValidationError, _session_validation_handler)
