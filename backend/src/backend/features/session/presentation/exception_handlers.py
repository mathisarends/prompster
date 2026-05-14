from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from backend.features.session.domain.exceptions import SessionNotFoundError


def _exception_detail(exc: Exception, *, fallback: str) -> str:
    detail = str(exc).strip()
    return detail if detail else fallback


async def _session_not_found_handler(
    _: Request,
    exc: SessionNotFoundError,
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": _exception_detail(exc, fallback="Session not found")},
    )


async def _bad_request_handler(_: Request, exc: ValueError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": _exception_detail(exc, fallback="Bad request")},
    )


def register_session_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(SessionNotFoundError, _session_not_found_handler)
    app.add_exception_handler(ValueError, _bad_request_handler)
