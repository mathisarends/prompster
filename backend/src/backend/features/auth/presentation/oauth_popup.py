import json

from fastapi.responses import HTMLResponse

_OAUTH_POPUP_MESSAGE_TYPE = "prompster-google-oauth"


class OAuthPopupResponse:
    @classmethod
    def success(cls, *, target_origin: str) -> HTMLResponse:
        return HTMLResponse(
            content=cls._build_html(
                target_origin=target_origin,
                status_value="success",
            )
        )

    @classmethod
    def error(cls, *, target_origin: str, reason: str) -> HTMLResponse:
        return HTMLResponse(
            content=cls._build_html(
                target_origin=target_origin,
                status_value="error",
                reason_value=reason,
            )
        )

    @staticmethod
    def _build_html(
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
