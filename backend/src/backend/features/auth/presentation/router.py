from fastapi import Query, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi_canon import APIRouter, CanonResponse, Inject

from backend.env import EnvSettings
from backend.features.auth.application import (
    GoogleOAuthFlow,
    SessionRefresher,
    SpotifyOAuthFlow,
)
from backend.features.auth.presentation.cookies import AuthCookies
from backend.features.auth.presentation.exceptions import (
    SESSION_EXPIRED_ERROR,
    SESSION_INVALID_ERROR,
)
from backend.features.auth.presentation.oauth_popup import OAuthPopupResponse
from backend.features.auth.presentation.oauth_state_cookies import (
    GoogleOAuthStateCookies,
    SpotifyLoginOAuthStateCookies,
)
from backend.presentation import RefreshAuthenticatedUserId

auth_router = APIRouter(
    prefix="/auth",
    tags=["auth"],
)


@auth_router.get(
    "/google/login",
    response_model=None,
    operation_id="google_login",
    response=CanonResponse.empty(
        status=status.HTTP_307_TEMPORARY_REDIRECT,
        description="Redirect to Google authorization.",
        headers=("Location",),
    ),
)
async def google_login(
    google_auth_flow: Inject[GoogleOAuthFlow],
    google_oauth_state_cookies: Inject[GoogleOAuthStateCookies],
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
    google_auth_flow: Inject[GoogleOAuthFlow],
    auth_cookies: Inject[AuthCookies],
    google_oauth_state_cookies: Inject[GoogleOAuthStateCookies],
    env_config: Inject[EnvSettings],
    *,
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
            target_origin=env_config.frontend_base_url
        )
        auth_cookies.set(response, result.session)
    else:
        response = OAuthPopupResponse.error(
            target_origin=env_config.frontend_base_url,
            reason=result.error_reason or "invalid_credentials",
        )

    google_oauth_state_cookies.clear(response)
    return response


@auth_router.get(
    "/spotify/login",
    response_model=None,
    operation_id="spotify_login",
    response=CanonResponse.empty(
        status=status.HTTP_307_TEMPORARY_REDIRECT,
        description="Redirect to Spotify authorization.",
        headers=("Location",),
    ),
)
async def spotify_login(
    spotify_oauth_flow: Inject[SpotifyOAuthFlow],
    spotify_login_state_cookies: Inject[SpotifyLoginOAuthStateCookies],
) -> RedirectResponse:
    authorization_request = spotify_oauth_flow.login()

    redirect_response = RedirectResponse(
        url=authorization_request.authorization_url,
        status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    )
    spotify_login_state_cookies.set(
        response=redirect_response,
        state=authorization_request.state,
    )
    return redirect_response


@auth_router.get(
    "/spotify/callback",
    response_model=None,
    operation_id="spotify_login_callback",
    include_in_schema=False,
)
async def spotify_login_callback(
    request: Request,
    spotify_oauth_flow: Inject[SpotifyOAuthFlow],
    auth_cookies: Inject[AuthCookies],
    spotify_login_state_cookies: Inject[SpotifyLoginOAuthStateCookies],
    env_config: Inject[EnvSettings],
    *,
    code: str | None = Query(default=None, min_length=1, max_length=4096),
    state: str = Query(min_length=1, max_length=4096),
    error: str | None = Query(default=None, min_length=1, max_length=256),
) -> HTMLResponse:
    result = await spotify_oauth_flow.callback(
        code=code,
        state=state,
        error=error,
        expected_oauth_state=spotify_login_state_cookies.read(request=request),
    )

    if result.succeeded and result.session is not None:
        response = OAuthPopupResponse.for_spotify_login(
            target_origin=env_config.frontend_base_url,
            succeeded=True,
            reason=None,
        )
        auth_cookies.set(response, result.session)
    else:
        response = OAuthPopupResponse.for_spotify_login(
            target_origin=env_config.frontend_base_url,
            succeeded=False,
            reason=result.error_reason or "invalid_credentials",
        )

    spotify_login_state_cookies.clear(response)
    return response


@auth_router.post(
    "/logout",
    response_model=None,
    operation_id="logout",
    response=CanonResponse.empty(),
)
async def logout(
    response: Response,
    auth_cookies: Inject[AuthCookies],
) -> None:
    auth_cookies.delete(response)


@auth_router.post(
    "/refresh",
    response_model=None,
    operation_id="refresh",
    raises=(
        SESSION_EXPIRED_ERROR,
        SESSION_INVALID_ERROR,
    ),
    response=CanonResponse.empty(),
)
async def refresh(
    authenticated_user_id: RefreshAuthenticatedUserId,
    response: Response,
    session_refresher: Inject[SessionRefresher],
    auth_cookies: Inject[AuthCookies],
) -> None:
    new_session = await session_refresher.refresh(user_id=authenticated_user_id)

    auth_cookies.set(response, new_session)
