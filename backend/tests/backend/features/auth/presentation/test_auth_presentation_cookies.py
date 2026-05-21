from fastapi import Response

from backend.env import EnvSettings
from backend.features.auth.application.schemas import AuthSession
from backend.features.auth.infrastructure.auth_settings import AuthSettings
from backend.features.auth.presentation.cookies import AuthCookies
from backend.features.auth.presentation.oauth_state_cookies import OAuthStateCookies


def _set_cookie_headers(response: Response) -> list[str]:
    return [
        value.decode("latin-1")
        for name, value in response.raw_headers
        if name == b"set-cookie"
    ]


class TestAuthCookies:
    def test_set_uses_host_only_cookies(self) -> None:
        response = Response()
        cookies = AuthCookies(
            auth_settings=AuthSettings(frontend_base_url="http://127.0.0.1:5173"),
            env_config=EnvSettings(frontend_base_url="http://127.0.0.1:5173"),
        )

        cookies.set(
            response=response,
            auth_session=AuthSession(
                access_token="access-1",
                refresh_token="refresh-1",
            ),
        )

        headers = _set_cookie_headers(response)
        active_cookie_headers = [
            header for header in headers if "Max-Age=0" not in header
        ]

        assert len(headers) == 2
        assert len(active_cookie_headers) == 2
        assert all("Domain=" not in header for header in active_cookie_headers)
        assert any(
            header.startswith("access_token=access-1")
            and "HttpOnly" in header
            and "SameSite=lax" in header
            for header in active_cookie_headers
        )
        assert any(
            header.startswith("refresh_token=refresh-1")
            and "HttpOnly" in header
            and "SameSite=lax" in header
            for header in active_cookie_headers
        )


class TestOAuthStateCookies:
    def test_set_uses_host_only_cookie_and_clears_legacy_domain_cookie(self) -> None:
        response = Response()
        cookies = OAuthStateCookies(
            cookie_name="oauth_state",
            ttl_seconds=120,
            signing_secret="secret-1",
            frontend_base_url="http://127.0.0.1:5173",
            env_config=EnvSettings(frontend_base_url="http://127.0.0.1:5173"),
        )

        cookies.set(response=response, state="state-1")

        headers = _set_cookie_headers(response)
        active_cookie_headers = [
            header for header in headers if "Max-Age=0" not in header
        ]

        assert len(headers) == 2
        assert len(active_cookie_headers) == 1
        assert active_cookie_headers[0].startswith("oauth_state=")
        assert "Domain=" not in active_cookie_headers[0]
        assert "HttpOnly" in active_cookie_headers[0]
        assert "Max-Age=120" in active_cookie_headers[0]
        assert any(
            header.startswith('oauth_state=""')
            and "Domain=127.0.0.1" in header
            and "Max-Age=0" in header
            for header in headers
        )
