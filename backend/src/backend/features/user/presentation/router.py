from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, status

from backend.features.auth.presentation.dependencies import AuthenticatedUserId
from backend.features.user.application import GetMeHandler
from backend.features.user.presentation.mapper import to_user_me_response
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
    authenticated_user_id: AuthenticatedUserId,
    handler: FromDishka[GetMeHandler],
) -> UserMeResponse:
    user = await handler.handle(user_id=authenticated_user_id)
    return to_user_me_response(user)
