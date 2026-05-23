from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Response, status

from backend.features.auth.presentation.dependencies import AuthenticatedUserId
from backend.features.user.application import UserService
from backend.features.user.presentation.mapper import to_user_me_response
from backend.features.user.presentation.schemas import (
    UserDeleteInformationResponse,
    UserMeResponse,
)
from backend.presentation.errors import ErrorDto

user_router = APIRouter(route_class=DishkaRoute, prefix="/users", tags=["users"])

_unauthorized = {status.HTTP_401_UNAUTHORIZED: {"model": ErrorDto}}


@user_router.get(
    "/me",
    response_model=UserMeResponse,
    status_code=status.HTTP_200_OK,
    operation_id="get_me",
    responses=_unauthorized,
)
async def get_me(
    authenticated_user_id: AuthenticatedUserId,
    service: FromDishka[UserService],
) -> UserMeResponse:
    user = await service.get_me(user_id=authenticated_user_id)
    return to_user_me_response(user)


@user_router.get(
    "/me/delete-information",
    response_model=UserDeleteInformationResponse,
    status_code=status.HTTP_200_OK,
    operation_id="get_delete_information",
    responses=_unauthorized,
)
async def get_delete_information(
    authenticated_user_id: AuthenticatedUserId,
    service: FromDishka[UserService],
) -> UserDeleteInformationResponse:
    delete_information = await service.get_delete_information(
        user_id=authenticated_user_id
    )
    return UserDeleteInformationResponse(
        session_count=delete_information.session_count,
    )


@user_router.delete(
    "/me",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    operation_id="delete_me",
    responses=_unauthorized,
)
async def delete_me(
    authenticated_user_id: AuthenticatedUserId,
    service: FromDishka[UserService],
) -> Response:
    await service.delete_me(user_id=authenticated_user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
