import pytest
from fastapi import Request, Response

from backend.env import EnvSettings
from backend.features.auth.presentation.cookies import AuthCookies
from backend.features.auth.presentation.oauth_state_cookies import OAuthStateCookies
from backend.presentation.authentication import AuthCookieSettings
from backend.shared.authentication import AuthSession

_COOKIE_SETTINGS = AuthCookieSettings(
    access_token_name="access_token",
    refresh_token_name="refresh_token",
    access_token_max_age_seconds=3600,
    refresh_token_max_age_seconds=86400,
    same_site_dev="lax",
    same_site_prod="strict",
)


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
            cookie_settings=_COOKIE_SETTINGS,
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
    @staticmethod
    def _cookies(*, ttl_seconds: int = 120) -> OAuthStateCookies:
        return OAuthStateCookies(
            cookie_name="oauth_state",
            ttl_seconds=ttl_seconds,
            signing_secret="secret-1",
            frontend_base_url="http://127.0.0.1:5173",
            env_config=EnvSettings(frontend_base_url="http://127.0.0.1:5173"),
        )

    @staticmethod
    def _request_with_cookie(value: str | None) -> Request:
        headers = (
            [] if value is None else [(b"cookie", f"oauth_state={value}".encode())]
        )
        return Request({"type": "http", "method": "GET", "headers": headers})

    def test_set_uses_host_only_cookie_and_clears_legacy_domain_cookie(self) -> None:
        response = Response()
        cookies = self._cookies()

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

    def test_round_trips_signed_state_and_uses_secure_cookies_in_production(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            "backend.features.auth.presentation.oauth_state_cookies.time.time",
            lambda: 1_000,
        )
        cookies = OAuthStateCookies(
            cookie_name="oauth_state",
            ttl_seconds=120,
            signing_secret="secret-1",
            frontend_base_url="https://app.example.com",
            env_config=EnvSettings(
                env="prod", frontend_base_url="https://app.example.com"
            ),
        )
        response = Response()

        cookies.set(response=response, state=" state-1 ")

        active_cookie = next(
            header
            for header in _set_cookie_headers(response)
            if "Max-Age=0" not in header
        )
        signed_state = active_cookie.split(";", maxsplit=1)[0].split("=", maxsplit=1)[1]
        assert (
            cookies.read(request=self._request_with_cookie(signed_state)) == "state-1"
        )
        assert "Secure" in active_cookie

    @pytest.mark.parametrize("state", ["", "   "])
    def test_rejects_empty_state(self, state: str) -> None:
        with pytest.raises(ValueError, match="state must not be empty"):
            self._cookies().set(response=Response(), state=state)

    def test_rejects_missing_tampered_and_expired_states(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            "backend.features.auth.presentation.oauth_state_cookies.time.time",
            lambda: 1_000,
        )
        cookies = self._cookies()
        signed_state = cookies._encode(state="state-1")

        assert cookies.read(request=self._request_with_cookie(None)) is None
        assert cookies.read(request=self._request_with_cookie("malformed")) is None
        assert (
            cookies.read(request=self._request_with_cookie(f"{signed_state}x")) is None
        )

        monkeypatch.setattr(
            "backend.features.auth.presentation.oauth_state_cookies.time.time",
            lambda: 1_121,
        )
        assert cookies.read(request=self._request_with_cookie(signed_state)) is None
