import asyncio
from typing import cast

from fastapi import Request
from fastapi.responses import HTMLResponse

from backend.features.auth.application import GoogleCallbackHandler
from backend.features.auth.infrastructure.auth_settings import AuthSettings
from backend.features.auth.presentation.cookies import AuthCookies
from backend.features.auth.presentation.router import google_callback


class _GoogleCallbackHandlerStub:
    def __init__(self) -> None:
        self.called = False

    async def handle(
        self,
        *,
        authorization_code: str,
        oauth_state: str,
        expected_oauth_state: str | None,
    ) -> object:
        self.called = True
        raise AssertionError("OAuth error callbacks must not exchange a code")


class _AuthCookiesStub:
    def __init__(self) -> None:
        self.clear_called = False

    def read_oauth_state(self, request: Request) -> str | None:
        return "state-1"

    def clear_oauth_state(self, response: HTMLResponse) -> None:
        self.clear_called = True


def _build_request() -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/api/v1/auth/google/callback",
            "headers": [],
            "query_string": b"error=access_denied&state=state-1",
        }
    )


class TestGoogleCallback:
    def test_access_denied_returns_popup_error(self) -> None:
        handler = _GoogleCallbackHandlerStub()
        auth_cookies = _AuthCookiesStub()

        response = asyncio.run(
            google_callback(
                request=_build_request(),
                handler=cast(GoogleCallbackHandler, handler),
                auth_cookies=cast(AuthCookies, auth_cookies),
                auth_settings=AuthSettings(frontend_base_url="http://localhost:5173"),
                code=None,
                state="state-1",
                error="access_denied",
            )
        )

        body = response.body.decode("utf-8")
        assert response.status_code == 200
        assert '"status": "error"' in body
        assert '"reason": "access_denied"' in body
        assert "http://localhost:5173" in body
        assert handler.called is False
        assert auth_cookies.clear_called is True

    def test_missing_code_returns_popup_error(self) -> None:
        handler = _GoogleCallbackHandlerStub()
        auth_cookies = _AuthCookiesStub()

        response = asyncio.run(
            google_callback(
                request=_build_request(),
                handler=cast(GoogleCallbackHandler, handler),
                auth_cookies=cast(AuthCookies, auth_cookies),
                auth_settings=AuthSettings(frontend_base_url="http://localhost:5173"),
                code=None,
                state="state-1",
                error=None,
            )
        )

        body = response.body.decode("utf-8")
        assert response.status_code == 200
        assert '"status": "error"' in body
        assert '"reason": "missing_code"' in body
        assert handler.called is False
        assert auth_cookies.clear_called is True
