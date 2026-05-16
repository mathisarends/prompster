from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Query, Response, status

from backend.features.auth.application import (
    GoogleCallbackHandler,
    RefreshSessionHandler,
)
from backend.features.auth.presentation.dependencies import AuthenticatedUserId
from backend.features.auth.presentation.cookies import AuthCookies
from backend.presentation.errors import ErrorDto

auth_router = APIRouter(
    route_class=DishkaRoute,
    prefix="/auth",
    tags=["auth"],
)

_error_responses = {
    401: {"model": ErrorDto, "description": "Invalid or expired credentials"},
}


@auth_router.get(
    "/google/callback",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    operation_id="google_callback",
    responses={401: _error_responses[401]},
)
async def google_callback(
    response: Response,
    handler: FromDishka[GoogleCallbackHandler],
    auth_cookies: FromDishka[AuthCookies],
    code: str = Query(min_length=1, max_length=4096),
) -> None:
    auth_session = await handler.handle(
        authorization_code=code,
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
    authenticated_user_id: AuthenticatedUserId,
    response: Response,
    handler: FromDishka[RefreshSessionHandler],
    auth_cookies: FromDishka[AuthCookies],
) -> None:
    new_session = await handler.handle(user_id=authenticated_user_id)

    auth_cookies.set(response, new_session)
