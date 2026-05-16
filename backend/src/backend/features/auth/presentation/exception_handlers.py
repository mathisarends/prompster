from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from backend.features.auth.application import (
    InvalidCredentialsException,
    SessionExpiredException,
    SessionInvalidException,
)


def _exception_detail(exc: Exception, *, fallback: str) -> str:
    detail = str(exc).strip()
    return detail if detail else fallback


async def _invalid_credentials_handler(
    _: Request,
    exc: InvalidCredentialsException,
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={
            "detail": _exception_detail(
                exc,
                fallback="Invalid or expired credentials",
            )
        },
    )


async def _refresh_session_invalid_handler(
    _: Request,
    exc: SessionExpiredException | SessionInvalidException,
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={
            "detail": _exception_detail(
                exc,
                fallback="Invalid or expired refresh token",
            )
        },
    )


def register_auth_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(
        InvalidCredentialsException,
        _invalid_credentials_handler,
    )
    app.add_exception_handler(
        SessionExpiredException,
        _refresh_session_invalid_handler,
    )
    app.add_exception_handler(
        SessionInvalidException,
        _refresh_session_invalid_handler,
    )
