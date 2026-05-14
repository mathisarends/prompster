from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, HTTPException, Request, Response, status

from backend.env import EnvSettings
from backend.features.auth.application import (
    LoginUserHandler,
    RefreshSessionHandler,
    RegisterUserHandler,
)
from backend.features.auth.infrastructure import AuthSettings
from backend.features.auth.presentation.cookies import AuthCookies
from backend.features.auth.presentation.schemas import (
    EmailPasswordRequest,
    RegisterRequest,
)
from backend.presentation.errors import ErrorDto

auth_router = APIRouter(
    route_class=DishkaRoute,
    prefix="/auth",
    tags=["auth"],
)

_error_responses = {
    401: {"model": ErrorDto, "description": "Invalid or expired credentials"},
    409: {"model": ErrorDto, "description": "Conflict"},
}


@auth_router.post(
    "/login",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    operation_id="login",
    responses={401: _error_responses[401]},
)
async def login(
    request: EmailPasswordRequest,
    response: Response,
    handler: FromDishka[LoginUserHandler],
    auth_cookies: FromDishka[AuthCookies],
) -> None:
    auth_session = await handler.handle(email=request.email, password=request.password)

    auth_cookies.set(response, auth_session)


@auth_router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    response_class=Response,
    operation_id="register",
    responses={
        404: {"description": "Registration disabled"},
        409: _error_responses[409],
    },
)
async def register(
    request: RegisterRequest,
    response: Response,
    handler: FromDishka[RegisterUserHandler],
    auth_cookies: FromDishka[AuthCookies],
    env_config: FromDishka[EnvSettings],
) -> None:
    if env_config.registration_disabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    auth_session = await handler.handle(
        name=request.name,
        email=request.email,
        password=request.password,
    )

    auth_cookies.set(response, auth_session)


@auth_router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    operation_id="logout",
)
async def logout(
    response: Response,
    auth_cookies: FromDishka[AuthCookies],
) -> None:
    auth_cookies.delete(response)


@auth_router.post(
    "/refresh",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    operation_id="refresh",
    responses={
        401: {"model": ErrorDto, "description": "Invalid or expired refresh token"},
    },
)
async def refresh(
    request: Request,
    response: Response,
    handler: FromDishka[RefreshSessionHandler],
    auth_cookies: FromDishka[AuthCookies],
    auth_settings: FromDishka[AuthSettings],
) -> None:
    token = request.cookies.get(auth_settings.jwt_refresh_token_cookie_name)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token required",
        )

    new_session = await handler.handle(refresh_token=token)

    auth_cookies.set(response, new_session)
