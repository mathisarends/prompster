from typing import Final
from urllib.parse import urlparse

from backend.features.auth.application.schemas import AuthSession
from backend.features.auth.infrastructure import AuthSettings
from fastapi import Response

from backend.env import EnvSettings


class AuthCookies:
    _SECONDS_PER_MINUTE: Final = 60
    _SECONDS_PER_DAY: Final = 60 * 60 * 24

    def __init__(self, auth_settings: AuthSettings, env_config: EnvSettings):
        self._auth_settings = auth_settings
        self._env_config = env_config
        self._domain = urlparse(auth_settings.frontend_base_url).hostname

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
        response.delete_cookie(
            key=self._auth_settings.access_token_cookie_name,
            path="/",
            domain=self._domain,
        )
        response.delete_cookie(
            key=self._auth_settings.jwt_refresh_token_cookie_name,
            path="/",
            domain=self._domain,
        )

    def _set_cookie(
        self, response: Response, key: str, value: str, max_age: int
    ) -> None:
        same_site = (
            self._auth_settings.cookie_samesite_prod
            if self._env_config.is_prod
            else self._auth_settings.cookie_samesite_dev
        )

        response.set_cookie(
            key=key,
            value=value,
            httponly=True,
            secure=self._env_config.is_prod,
            samesite=same_site,
            domain=self._domain,
            path="/",
            max_age=max_age,
        )
