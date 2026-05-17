import json

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Query, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse

from backend.features.auth.application import (
    GoogleCallbackHandler,
    GoogleLoginHandler,
    RefreshSessionHandler,
)
from backend.features.auth.application.exceptions import InvalidCredentialsException
from backend.features.auth.infrastructure.auth_settings import AuthSettings
from backend.features.auth.presentation.dependencies import AuthenticatedUserId
from backend.features.auth.presentation.cookies import AuthCookies
from backend.presentation.errors import ErrorDto

_OAUTH_POPUP_MESSAGE_TYPE = "prompster-google-oauth"


def _build_oauth_popup_html(
    *,
    target_origin: str,
    status_value: str,
    reason_value: str | None = None,
) -> str:
    payload = {"type": _OAUTH_POPUP_MESSAGE_TYPE, "status": status_value}
    if reason_value is not None:
        payload["reason"] = reason_value

    payload_js = json.dumps(payload)
    target_origin_js = json.dumps(target_origin)
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><title>Google sign-in</title></head>
<body>
<script>
  (function () {{
    if (window.opener) {{
      try {{ window.opener.postMessage({payload_js}, {target_origin_js}); }} catch (e) {{}}
    }}
    window.close();
  }})();
</script>
</body>
</html>"""


auth_router = APIRouter(
    route_class=DishkaRoute,
    prefix="/auth",
    tags=["auth"],
)

_invalid_credentials = {
    status.HTTP_401_UNAUTHORIZED: {
        "model": ErrorDto,
        "description": "Invalid or expired credentials",
    },
}
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
    handler: FromDishka[GoogleLoginHandler],
    auth_cookies: FromDishka[AuthCookies],
) -> RedirectResponse:
    authorization_request = handler.handle()

    redirect_response = RedirectResponse(
        url=authorization_request.authorization_url,
        status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    )
    auth_cookies.set_oauth_state(
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
    handler: FromDishka[GoogleCallbackHandler],
    auth_cookies: FromDishka[AuthCookies],
    auth_settings: FromDishka[AuthSettings],
    code: str | None = Query(default=None, min_length=1, max_length=4096),
    state: str = Query(min_length=1, max_length=4096),
    error: str | None = Query(default=None, min_length=1, max_length=256),
) -> HTMLResponse:
    expected_oauth_state = auth_cookies.read_oauth_state(request=request)

    if error is not None or code is None:
        response = HTMLResponse(
            content=_build_oauth_popup_html(
                target_origin=auth_settings.frontend_base_url,
                status_value="error",
                reason_value=error or "missing_code",
            )
        )
        auth_cookies.clear_oauth_state(response)
        return response

    try:
        auth_session = await handler.handle(
            authorization_code=code,
            oauth_state=state,
            expected_oauth_state=expected_oauth_state,
        )
        response = HTMLResponse(
            content=_build_oauth_popup_html(
                target_origin=auth_settings.frontend_base_url,
                status_value="success",
            )
        )
        auth_cookies.set(response, auth_session)
    except InvalidCredentialsException:
        response = HTMLResponse(
            content=_build_oauth_popup_html(
                target_origin=auth_settings.frontend_base_url,
                status_value="error",
                reason_value="invalid_credentials",
            )
        )

    auth_cookies.clear_oauth_state(response)
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
    authenticated_user_id: AuthenticatedUserId,
    response: Response,
    handler: FromDishka[RefreshSessionHandler],
    auth_cookies: FromDishka[AuthCookies],
) -> None:
    new_session = await handler.handle(user_id=authenticated_user_id)

    auth_cookies.set(response, new_session)
