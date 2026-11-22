from fastapi import Response, status
from fastapi_canon import APIRouter, CanonResponse, Inject

from backend.features.user.application import UserService
from backend.features.user.presentation.mapper import to_user_me_response
from backend.features.user.presentation.schemas import (
    UserDeleteInformationResponse,
    UserMeResponse,
)
from backend.presentation import (
    AUTHENTICATION_REQUIRED_ERROR,
    AuthenticatedUserId,
)

user_router = APIRouter(
    prefix="/users",
    tags=["users"],
    raises=(AUTHENTICATION_REQUIRED_ERROR,),
)


@user_router.get(
    "/me",
    response_model=UserMeResponse,
    status_code=status.HTTP_200_OK,
    operation_id="get_me",
)
async def get_me(
    authenticated_user_id: AuthenticatedUserId,
    service: Inject[UserService],
) -> UserMeResponse:
    user = await service.get_me(user_id=authenticated_user_id)
    return to_user_me_response(user=user)


@user_router.get(
    "/me/delete-information",
    response_model=UserDeleteInformationResponse,
    status_code=status.HTTP_200_OK,
    operation_id="get_delete_information",
)
async def get_delete_information(
    authenticated_user_id: AuthenticatedUserId,
    service: Inject[UserService],
) -> UserDeleteInformationResponse:
    delete_information = await service.get_delete_information(
        user_id=authenticated_user_id
    )
    return UserDeleteInformationResponse(
        session_count=delete_information.session_count,
    )


@user_router.delete(
    "/me",
    response_model=None,
    operation_id="delete_me",
    response=CanonResponse.empty(),
)
async def delete_me(
    authenticated_user_id: AuthenticatedUserId,
    service: Inject[UserService],
) -> Response:
    await service.delete_me(user_id=authenticated_user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
