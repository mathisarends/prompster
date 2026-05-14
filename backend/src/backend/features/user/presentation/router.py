from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, HTTPException, Request, status

from backend.features.auth.domain import AuthUserRepository
from backend.features.auth.infrastructure import AuthSettings
from backend.features.user.presentation import mapper as mapper
from backend.features.user.presentation.schemas import UserMeResponse
from backend.presentation.errors import ErrorDto

user_router = APIRouter(route_class=DishkaRoute, prefix="/users", tags=["users"])


@user_router.get(
    "/me",
    response_model=UserMeResponse,
    status_code=status.HTTP_200_OK,
    operation_id="get_me",
    responses={status.HTTP_401_UNAUTHORIZED: {"model": ErrorDto}},
)
async def get_me(
    request: Request,
    user_repository: FromDishka[AuthUserRepository],
    auth_settings: FromDishka[AuthSettings],
) -> UserMeResponse:
    token = request.cookies.get(auth_settings.access_token_cookie_name)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    user_id = mapper.extract_user_id(token, auth_settings=auth_settings)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token",
        )

    auth_user = await user_repository.get_by_id(user_id=user_id)
    if auth_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token",
        )

    user = mapper.to_user(auth_user)
    return UserMeResponse(
        id=user.id,
        name=user.name,
        email=user.email,
        created_at=user.created_at,
    )
