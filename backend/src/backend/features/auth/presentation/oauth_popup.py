import json

from fastapi.responses import HTMLResponse


class OAuthPopupResponse:
    @classmethod
    def success(cls, *, target_origin: str) -> HTMLResponse:
        return cls.for_google(
            target_origin=target_origin,
            succeeded=True,
            reason=None,
        )

    @classmethod
    def error(cls, *, target_origin: str, reason: str) -> HTMLResponse:
        return cls.for_google(
            target_origin=target_origin,
            succeeded=False,
            reason=reason,
        )

    @classmethod
    def for_google(
        cls,
        *,
        target_origin: str,
        succeeded: bool,
        reason: str | None,
    ) -> HTMLResponse:
        return HTMLResponse(
            content=_build_html(
                message_type=_OAUTH_POPUP_MESSAGE_TYPE,
                target_origin=target_origin,
                status_value="success" if succeeded else "error",
                reason_value=reason,
            )
        )

    @classmethod
    def for_spotify(
        cls,
        *,
        target_origin: str,
        succeeded: bool,
        reason: str | None,
    ) -> HTMLResponse:
        return HTMLResponse(
            content=_build_html(
                message_type=_SPOTIFY_OAUTH_POPUP_MESSAGE_TYPE,
                target_origin=target_origin,
                status_value="success" if succeeded else "error",
                reason_value=reason,
            )
        )

    @classmethod
    def for_spotify_login(
        cls,
        *,
        target_origin: str,
        succeeded: bool,
        reason: str | None,
    ) -> HTMLResponse:
        return HTMLResponse(
            content=_build_html(
                message_type=_SPOTIFY_LOGIN_POPUP_MESSAGE_TYPE,
                target_origin=target_origin,
                status_value="success" if succeeded else "error",
                reason_value=reason,
            )
        )


_OAUTH_POPUP_MESSAGE_TYPE = "prompster-google-oauth"
_SPOTIFY_OAUTH_POPUP_MESSAGE_TYPE = "prompster-spotify-oauth"
_SPOTIFY_LOGIN_POPUP_MESSAGE_TYPE = "prompster-spotify-login"


def _build_html(
    *,
    message_type: str,
    target_origin: str,
    status_value: str,
    reason_value: str | None = None,
) -> str:
    payload = {"type": message_type, "status": status_value}
    if reason_value is not None:
        payload["reason"] = reason_value

    payload_js = json.dumps(payload)
    target_origin_js = json.dumps(target_origin)
    return f"""<!DOCTYPE html>
l lang="en">
d><meta charset="utf-8"><title>Google sign-in</title></head>
y>
ipt>
unction () {{
if (window.opener) {{
  try {{ window.opener.postMessage({payload_js}, {target_origin_js}); }} catch (e) {{}}
}}
window.close();
)();
ript>
dy>
ml>"""
