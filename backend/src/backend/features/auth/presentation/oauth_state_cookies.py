import base64
import hashlib
import hmac
import time
from urllib.parse import urlparse

from fastapi import Request, Response

from backend.env import EnvSettings


class OAuthStateCookies:
    """Signed, short-lived state cookie for an OAuth authorization flow.

    Generic over the cookie name so the same logic serves every provider.
    """

    def __init__(
        self,
        *,
        cookie_name: str,
        ttl_seconds: int,
        signing_secret: str,
        frontend_base_url: str,
        env_config: EnvSettings,
    ) -> None:
        self._cookie_name = cookie_name
        self._ttl_seconds = ttl_seconds
        self._signing_key = signing_secret.encode("utf-8")
        self._legacy_domain = urlparse(frontend_base_url).hostname
        self._env_config = env_config

    def set(self, *, response: Response, state: str) -> None:
        normalized_state = state.strip()
        if not normalized_state:
            raise ValueError("OAuth state must not be empty")

        signed_state = self._encode(state=normalized_state)
        self._delete_legacy_domain_cookie(response=response)
        response.set_cookie(
            key=self._cookie_name,
            value=signed_state,
            httponly=True,
            secure=self._env_config.is_prod,
            samesite="lax",
            path="/",
            max_age=self._ttl_seconds,
        )

    def read(self, *, request: Request) -> str | None:
        signed_state = request.cookies.get(self._cookie_name)
        if not signed_state:
            return None
        return self._decode(signed_state=signed_state)

    def clear(self, response: Response) -> None:
        response.delete_cookie(
            key=self._cookie_name,
            path="/",
        )
        self._delete_legacy_domain_cookie(response=response)

    def _delete_legacy_domain_cookie(self, *, response: Response) -> None:
        if self._legacy_domain is None:
            return

        response.delete_cookie(
            key=self._cookie_name,
            path="/",
            domain=self._legacy_domain,
        )

    def _encode(self, *, state: str) -> str:
        issued_at = str(int(time.time()))
        signature = self._sign(issued_at=issued_at, state=state)
        return f"{issued_at}.{state}.{signature}"

    def _decode(self, *, signed_state: str) -> str | None:
        first_separator_index = signed_state.find(".")
        last_separator_index = signed_state.rfind(".")
        if (
            first_separator_index <= 0
            or last_separator_index <= first_separator_index + 1
            or last_separator_index >= len(signed_state) - 1
        ):
            return None

        issued_at = signed_state[:first_separator_index]
        state = signed_state[first_separator_index + 1 : last_separator_index]
        received_signature = signed_state[last_separator_index + 1 :]

        if not issued_at.isdigit() or not state:
            return None

        expected_signature = self._sign(issued_at=issued_at, state=state)
        if not hmac.compare_digest(expected_signature, received_signature):
            return None

        signed_at_unix_seconds = int(issued_at)
        current_unix_seconds = int(time.time())
        token_age = current_unix_seconds - signed_at_unix_seconds
        if token_age < 0 or token_age > self._ttl_seconds:
            return None

        return state

    def _sign(self, *, issued_at: str, state: str) -> str:
        payload = f"{issued_at}.{state}".encode("utf-8")
        signature = hmac.new(
            self._signing_key,
            payload,
            hashlib.sha256,
        ).digest()
        return base64.urlsafe_b64encode(signature).rstrip(b"=").decode("ascii")


class GoogleOAuthStateCookies(OAuthStateCookies):
    """OAuth state cookie for the Google login flow.

    Subclass exists purely for DI type discrimination.
    """
