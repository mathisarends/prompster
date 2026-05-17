import base64
import hashlib
import hmac
import time
from typing import Final
from urllib.parse import urlparse

from fastapi import Request, Response

from backend.env import EnvSettings
from backend.features.auth.application.schemas import AuthSession
from backend.features.auth.infrastructure import AuthSettings


class AuthCookies:
    _SECONDS_PER_MINUTE: Final = 60
    _SECONDS_PER_DAY: Final = 60 * 60 * 24

    def __init__(self, auth_settings: AuthSettings, env_config: EnvSettings):
        self._auth_settings = auth_settings
        self._env_config = env_config
        self._domain = urlparse(auth_settings.frontend_base_url).hostname
        self._state_signing_key = auth_settings.jwt_secret.encode("utf-8")

    def set(self, response: Response, auth_session: AuthSession) -> None:
        self._set_cookie(
            response=response,
            key=self._auth_settings.access_token_cookie_name,
            value=auth_session.access_token,
            max_age=self._auth_settings.jwt_access_token_expire_minutes
            * self._SECONDS_PER_MINUTE,
        )
        self._set_cookie(
            response=response,
            key=self._auth_settings.jwt_refresh_token_cookie_name,
            value=auth_session.refresh_token,
            max_age=self._auth_settings.jwt_refresh_token_expire_days
            * self._SECONDS_PER_DAY,
        )

    def delete(self, response: Response) -> None:
        self._delete_cookie(
            response=response,
            key=self._auth_settings.access_token_cookie_name,
        )
        self._delete_cookie(
            response=response,
            key=self._auth_settings.jwt_refresh_token_cookie_name,
        )
        self._delete_cookie(
            response=response,
            key=self._auth_settings.oauth_state_cookie_name,
        )

    def set_oauth_state(self, response: Response, state: str) -> None:
        normalized_state = state.strip()
        if not normalized_state:
            raise ValueError("OAuth state must not be empty")

        signed_state = self._encode_signed_oauth_state(state=normalized_state)
        self._set_cookie(
            response=response,
            key=self._auth_settings.oauth_state_cookie_name,
            value=signed_state,
            max_age=self._auth_settings.oauth_state_ttl_seconds,
            same_site="lax",
        )

    def pop_oauth_state(self, request: Request, response: Response) -> str | None:
        signed_state = request.cookies.get(self._auth_settings.oauth_state_cookie_name)
        self._delete_cookie(
            response=response,
            key=self._auth_settings.oauth_state_cookie_name,
        )

        if not signed_state:
            return None

        return self._decode_signed_oauth_state(signed_state=signed_state)

    def _set_cookie(
        self,
        response: Response,
        key: str,
        value: str,
        max_age: int,
        same_site: str | None = None,
    ) -> None:
        cookie_same_site = same_site or (
            self._auth_settings.cookie_samesite_prod
            if self._env_config.is_prod
            else self._auth_settings.cookie_samesite_dev
        )

        response.set_cookie(
            key=key,
            value=value,
            httponly=True,
            secure=self._env_config.is_prod,
            samesite=cookie_same_site,
            domain=self._domain,
            path="/",
            max_age=max_age,
        )

    def _delete_cookie(self, response: Response, key: str) -> None:
        response.delete_cookie(
            key=key,
            path="/",
            domain=self._domain,
        )

    def _encode_signed_oauth_state(self, *, state: str) -> str:
        issued_at = str(int(time.time()))
        signature = self._sign_state_payload(issued_at=issued_at, state=state)
        return f"{issued_at}.{state}.{signature}"

    def _decode_signed_oauth_state(self, *, signed_state: str) -> str | None:
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

        expected_signature = self._sign_state_payload(issued_at=issued_at, state=state)
        if not hmac.compare_digest(expected_signature, received_signature):
            return None

        signed_at_unix_seconds = int(issued_at)
        current_unix_seconds = int(time.time())
        max_token_age = self._auth_settings.oauth_state_ttl_seconds
        token_age = current_unix_seconds - signed_at_unix_seconds
        if token_age < 0 or token_age > max_token_age:
            return None

        return state

    def _sign_state_payload(self, *, issued_at: str, state: str) -> str:
        payload = f"{issued_at}.{state}".encode("utf-8")
        signature = hmac.new(
            self._state_signing_key,
            payload,
            hashlib.sha256,
        ).digest()
        return base64.urlsafe_b64encode(signature).rstrip(b"=").decode("ascii")
