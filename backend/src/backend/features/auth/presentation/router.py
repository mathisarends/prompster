from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Query, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse

from backend.features.auth.application import (
    GoogleOAuthFlow,
    SessionRefresher,
)
from backend.features.auth.infrastructure.auth_settings import AuthSettings
from backend.features.auth.presentation.cookies import AuthCookies
from backend.features.auth.presentation.dependencies import (
    RefreshAuthenticatedUserId,
)
from backend.features.auth.presentation.oauth_popup import OAuthPopupResponse
from backend.features.auth.presentation.oauth_state_cookies import (
    GoogleOAuthStateCookies,
)
from backend.presentation.errors import ErrorDto

auth_router = APIRouter(
    route_class=DishkaRoute,
    prefix="/auth",
    tags=["auth"],
)

_invalid_refresh_token = {
    status.HTTP_401_UNAUTHORIZED: {
        "model": ErrorDto,
        "description": "Invalid or expired refresh token",
    },
}


@auth_router.get(
    "/google/login",
    status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    response_model=None,
    operation_id="google_login",
)
async def google_login(
    google_auth_flow: FromDishka[GoogleOAuthFlow],
    google_oauth_state_cookies: FromDishka[GoogleOAuthStateCookies],
) -> RedirectResponse:
    authorization_request = google_auth_flow.login()

    redirect_response = RedirectResponse(
        url=authorization_request.authorization_url,
        status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    )
    google_oauth_state_cookies.set(
        response=redirect_response,
        state=authorization_request.state,
    )
    return redirect_response


@auth_router.get(
    "/google/callback",
    response_model=None,
    operation_id="google_callback",
    include_in_schema=False,
)
async def google_callback(
    request: Request,
    google_auth_flow: FromDishka[GoogleOAuthFlow],
    auth_cookies: FromDishka[AuthCookies],
    google_oauth_state_cookies: FromDishka[GoogleOAuthStateCookies],
    auth_settings: FromDishka[AuthSettings],
    code: str | None = Query(default=None, min_length=1, max_length=4096),
    state: str = Query(min_length=1, max_length=4096),
    error: str | None = Query(default=None, min_length=1, max_length=256),
) -> HTMLResponse:
    result = await google_auth_flow.callback(
        code=code,
        state=state,
        error=error,
        expected_oauth_state=google_oauth_state_cookies.read(request=request),
    )

    if result.succeeded and result.session is not None:
        response = OAuthPopupResponse.success(
            target_origin=auth_settings.frontend_base_url
        )
        auth_cookies.set(response, result.session)
    else:
        response = OAuthPopupResponse.error(
            target_origin=auth_settings.frontend_base_url,
            reason=result.error_reason or "invalid_credentials",
        )

    google_oauth_state_cookies.clear(response)
    return response


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
    responses=_invalid_refresh_token,
)
async def refresh(
    authenticated_user_id: RefreshAuthenticatedUserId,
    response: Response,
    session_refresher: FromDishka[SessionRefresher],
    auth_cookies: FromDishka[AuthCookies],
) -> None:
    new_session = await session_refresher.refresh(user_id=authenticated_user_id)

    auth_cookies.set(response, new_session)
