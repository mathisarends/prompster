from backend.features.auth.presentation.dependencies import AuthenticatedUserId
from backend.features.auth.presentation.exceptions import (
    AUTHENTICATION_REQUIRED_ERROR,
)
from backend.features.oauth_connections.application import (
    SpotifyOAuthConnectionService,
    SpotifyTokenService,
)
from backend.features.oauth_connections.presentation.exceptions import (
    SPOTIFY_CONNECTION_NOT_FOUND_ERROR,
    SPOTIFY_TOKEN_REVOKED_ERROR,
)
from backend.features.oauth_connections.presentation.schemas import (
    SpotifyAccessTokenResponse,
)
from backend.features.oauth_connections.presentation.spotify_oauth_state_cookies import (
    SpotifyOAuthStateCookies,
)
from fastapi import Response, status
from fastapi.responses import RedirectResponse
from fastapi_canon import APIRouter, CanonResponse, Inject

spotify_oauth_router = APIRouter(
    prefix="/auth/spotify",
    tags=["spotify"],
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
    service: Inject[SpotifyOAuthConnectionService],
    spotify_oauth_state_cookies: Inject[SpotifyOAuthStateCookies],
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


@spotify_oauth_router.delete(
    "",
    response_model=None,
    operation_id="spotify_disconnect",
    response=CanonResponse.empty(),
)
async def spotify_disconnect(
    authenticated_user_id: AuthenticatedUserId,
    service: Inject[SpotifyOAuthConnectionService],
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
    token_service: Inject[SpotifyTokenService],
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
