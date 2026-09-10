from backend.features.auth.infrastructure.auth_settings import AuthSettings
from backend.features.auth.presentation.dependencies import AuthenticatedUserId
from backend.features.auth.presentation.exceptions import (
    AUTHENTICATION_REQUIRED_ERROR,
)
from backend.features.auth.presentation.oauth_popup import OAuthPopupResponse
from backend.features.oauth_connections.application import (
    SpotifyOAuthConnectionService,
    SpotifyTokenService,
)
from backend.features.oauth_connections.presentation.exceptions import (
    OAUTH_CONNECTION_ERRORS,
    SPOTIFY_CONNECTION_NOT_FOUND_ERROR,
    SPOTIFY_TOKEN_REVOKED_ERROR,
)
from backend.features.oauth_connections.presentation.schemas import (
    SpotifyAccessTokenResponse,
)
from backend.features.oauth_connections.presentation.spotify_oauth_state_cookies import (
    SpotifyOAuthStateCookies,
)
from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import Query, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi_canon import CanonResponse, CanonRouter

spotify_oauth_router = CanonRouter(
    route_class=DishkaRoute,
    prefix="/auth/spotify",
    tags=["spotify"],
    error_registry=OAUTH_CONNECTION_ERRORS,
    raises=(AUTHENTICATION_REQUIRED_ERROR,),
)


@spotify_oauth_router.get(
    "/connect",
    response_model=None,
    operation_id="spotify_connect",
    response=CanonResponse.empty(
        status=status.HTTP_307_TEMPORARY_REDIRECT,
        description="Redirect to Spotify authorization.",
        headers=("Location",),
    ),
)
async def spotify_connect(
    authenticated_user_id: AuthenticatedUserId,
    service: FromDishka[SpotifyOAuthConnectionService],
    spotify_oauth_state_cookies: FromDishka[SpotifyOAuthStateCookies],
) -> RedirectResponse:
    authorization_request = service.start_connect(user_id=authenticated_user_id)
    response = RedirectResponse(
        url=authorization_request.authorization_url,
        status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    )
    spotify_oauth_state_cookies.set(
        response=response,
        state=authorization_request.state,
    )
    return response


@spotify_oauth_router.get(
    "/callback",
    response_model=None,
    operation_id="spotify_callback",
    include_in_schema=False,
)
async def spotify_callback(
    request: Request,
    authenticated_user_id: AuthenticatedUserId,
    service: FromDishka[SpotifyOAuthConnectionService],
    spotify_oauth_state_cookies: FromDishka[SpotifyOAuthStateCookies],
    auth_settings: FromDishka[AuthSettings],
    code: str | None = Query(default=None, min_length=1, max_length=4096),
    state: str = Query(min_length=1, max_length=4096),
    error: str | None = Query(default=None, min_length=1, max_length=256),
) -> HTMLResponse:
    result = await service.complete_connect(
        authenticated_user_id=authenticated_user_id,
        code=code,
        state=state,
        error=error,
        expected_oauth_state=spotify_oauth_state_cookies.read(request=request),
    )
    response = OAuthPopupResponse.for_spotify(
        target_origin=auth_settings.frontend_base_url,
        succeeded=result.succeeded,
        reason=result.error_reason,
    )
    spotify_oauth_state_cookies.clear(response)
    return response


@spotify_oauth_router.delete(
    "",
    response_model=None,
    operation_id="spotify_disconnect",
    response=CanonResponse.empty(),
)
async def spotify_disconnect(
    authenticated_user_id: AuthenticatedUserId,
    service: FromDishka[SpotifyOAuthConnectionService],
) -> None:
    await service.disconnect(user_id=authenticated_user_id)


@spotify_oauth_router.get(
    "/token",
    response_model=SpotifyAccessTokenResponse,
    status_code=status.HTTP_200_OK,
    operation_id="spotify_get_access_token",
    raises=(
        SPOTIFY_CONNECTION_NOT_FOUND_ERROR,
        SPOTIFY_TOKEN_REVOKED_ERROR,
    ),
)
async def spotify_get_access_token(
    authenticated_user_id: AuthenticatedUserId,
    response: Response,
    token_service: FromDishka[SpotifyTokenService],
) -> SpotifyAccessTokenResponse:
    response.headers["Cache-Control"] = "no-store"

    access_token = await token_service.get_valid_access_token(
        user_id=authenticated_user_id,
    )

    return SpotifyAccessTokenResponse(
        access_token=access_token.access_token,
        expires_in=access_token.expires_in,
        scope=access_token.scope,
    )
