from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, HTTPException, Query, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse

from backend.features.auth.infrastructure.auth_settings import AuthSettings
from backend.features.auth.presentation.cookies import AuthCookies
from backend.features.auth.presentation.dependencies import AuthenticatedUserId
from backend.features.auth.presentation.oauth_popup import OAuthPopupResponse
from backend.features.oauth_connections.application import (
    ConnectSpotifyHandler,
    DisconnectSpotifyHandler,
    SpotifyConnectionNotFoundException,
    SpotifyTokenRevokedException,
    SpotifyTokenService,
)
from backend.features.oauth_connections.presentation.schemas import (
    SpotifyAccessTokenResponse,
)
from backend.presentation.errors import ErrorDto

spotify_oauth_router = APIRouter(
    route_class=DishkaRoute,
    prefix="/auth/spotify",
    tags=["spotify"],
)

_spotify_token_errors = {
    status.HTTP_409_CONFLICT: {
        "model": ErrorDto,
        "description": "Spotify not connected",
    },
    status.HTTP_410_GONE: {
        "model": ErrorDto,
        "description": "Spotify access revoked, reconnect required",
    },
}


@spotify_oauth_router.get(
    "/connect",
    status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    response_model=None,
    operation_id="spotify_connect",
)
async def spotify_connect(
    authenticated_user_id: AuthenticatedUserId,
    handler: FromDishka[ConnectSpotifyHandler],
    auth_cookies: FromDishka[AuthCookies],
) -> RedirectResponse:
    authorization_request = handler.start(user_id=authenticated_user_id)
    response = RedirectResponse(
        url=authorization_request.authorization_url,
        status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    )
    auth_cookies.set_spotify_oauth_state(
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
    handler: FromDishka[ConnectSpotifyHandler],
    auth_cookies: FromDishka[AuthCookies],
    auth_settings: FromDishka[AuthSettings],
    code: str | None = Query(default=None, min_length=1, max_length=4096),
    state: str = Query(min_length=1, max_length=4096),
    error: str | None = Query(default=None, min_length=1, max_length=256),
) -> HTMLResponse:
    result = await handler.complete(
        authenticated_user_id=authenticated_user_id,
        code=code,
        state=state,
        error=error,
        expected_oauth_state=auth_cookies.read_spotify_oauth_state(request=request),
    )
    response = OAuthPopupResponse.for_spotify(
        target_origin=auth_settings.frontend_base_url,
        succeeded=result.succeeded,
        reason=result.error_reason,
    )
    auth_cookies.clear_spotify_oauth_state(response)
    return response


@spotify_oauth_router.delete(
    "",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    operation_id="spotify_disconnect",
)
async def spotify_disconnect(
    authenticated_user_id: AuthenticatedUserId,
    handler: FromDishka[DisconnectSpotifyHandler],
) -> None:
    await handler.handle(user_id=authenticated_user_id)


@spotify_oauth_router.get(
    "/token",
    response_model=SpotifyAccessTokenResponse,
    status_code=status.HTTP_200_OK,
    operation_id="spotify_get_access_token",
    responses=_spotify_token_errors,
)
async def spotify_get_access_token(
    authenticated_user_id: AuthenticatedUserId,
    response: Response,
    token_service: FromDishka[SpotifyTokenService],
) -> SpotifyAccessTokenResponse:
    response.headers["Cache-Control"] = "no-store"

    try:
        access_token = await token_service.get_valid_access_token(
            user_id=authenticated_user_id,
        )
    except SpotifyConnectionNotFoundException as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Spotify is not connected",
        ) from exc
    except SpotifyTokenRevokedException as exc:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Spotify access revoked, please reconnect",
        ) from exc

    return SpotifyAccessTokenResponse(
        access_token=access_token.access_token,
        expires_in=access_token.expires_in,
        scope=access_token.scope,
    )
