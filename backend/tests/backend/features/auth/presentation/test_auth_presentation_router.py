import asyncio
from typing import cast

from fastapi import Request
from fastapi.responses import HTMLResponse

from backend.features.auth.application import GoogleOAuthFlow
from backend.features.auth.application.schemas import GoogleCallbackResult
from backend.features.auth.infrastructure.auth_settings import AuthSettings
from backend.features.auth.presentation.cookies import AuthCookies
from backend.features.auth.presentation.oauth_state_cookies import (
    GoogleOAuthStateCookies,
)
from backend.features.auth.presentation.router import google_callback


class _GoogleOAuthFlowStub:
    def __init__(self) -> None:
        self.received_code: str | None = None
        self.received_state: str | None = None
        self.received_error: str | None = None
        self.received_expected_oauth_state: str | None = None

    async def callback(
        self,
        *,
        code: str | None,
        state: str,
        error: str | None,
        expected_oauth_state: str | None,
    ) -> GoogleCallbackResult:
        self.received_code = code
        self.received_state = state
        self.received_error = error
        self.received_expected_oauth_state = expected_oauth_state

        if error is not None:
            return GoogleCallbackResult.error(reason=error)
        return GoogleCallbackResult.error(reason="missing_code")


class _AuthCookiesStub:
    def set(self, response: HTMLResponse, auth_session: object) -> None:
        pass


class _GoogleOAuthStateCookiesStub:
    def __init__(self) -> None:
        self.clear_called = False

    def read(self, *, request: Request) -> str | None:
        return "state-1"

    def clear(self, response: HTMLResponse) -> None:
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
        handler = _GoogleOAuthFlowStub()
        auth_cookies = _AuthCookiesStub()
        state_cookies = _GoogleOAuthStateCookiesStub()

        response = asyncio.run(
            google_callback(
                request=_build_request(),
                handler=cast(GoogleOAuthFlow, handler),
                auth_cookies=cast(AuthCookies, auth_cookies),
                google_oauth_state_cookies=cast(GoogleOAuthStateCookies, state_cookies),
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
        assert handler.received_code is None
        assert handler.received_state == "state-1"
        assert handler.received_error == "access_denied"
        assert handler.received_expected_oauth_state == "state-1"
        assert state_cookies.clear_called is True

    def test_missing_code_returns_popup_error(self) -> None:
        handler = _GoogleOAuthFlowStub()
        auth_cookies = _AuthCookiesStub()
        state_cookies = _GoogleOAuthStateCookiesStub()

        response = asyncio.run(
            google_callback(
                request=_build_request(),
                handler=cast(GoogleOAuthFlow, handler),
                auth_cookies=cast(AuthCookies, auth_cookies),
                google_oauth_state_cookies=cast(GoogleOAuthStateCookies, state_cookies),
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
        assert handler.received_code is None
        assert handler.received_state == "state-1"
        assert handler.received_error is None
        assert handler.received_expected_oauth_state == "state-1"
        assert state_cookies.clear_called is True
