from fastapi import Response

from backend.env import EnvSettings
from backend.shared.authentication import AuthSession
from backend.presentation.authentication import AuthCookieSettings


class AuthCookies:
    def __init__(self, cookie_settings: AuthCookieSettings, env_config: EnvSettings):
        self._cookie_settings = cookie_settings
        self._env_config = env_config

    def set(self, response: Response, auth_session: AuthSession) -> None:
        self._set_cookie(
            response=response,
            key=self._cookie_settings.access_token_name,
            value=auth_session.access_token,
            max_age=self._cookie_settings.access_token_max_age_seconds,
        )
        self._set_cookie(
            response=response,
            key=self._cookie_settings.refresh_token_name,
            value=auth_session.refresh_token,
            max_age=self._cookie_settings.refresh_token_max_age_seconds,
        )

    def delete(self, response: Response) -> None:
        response.delete_cookie(
            key=self._cookie_settings.access_token_name,
            path="/",
        )
        response.delete_cookie(
            key=self._cookie_settings.refresh_token_name,
            path="/",
        )

    def _set_cookie(
        self,
        response: Response,
        key: str,
        value: str,
        max_age: int,
    ) -> None:
        cookie_same_site = (
            self._cookie_settings.same_site_prod
            if self._env_config.is_prod
            else self._cookie_settings.same_site_dev
        )

        response.set_cookie(
            key=key,
            value=value,
            httponly=True,
            secure=self._env_config.is_prod,
            samesite=cookie_same_site,
            path="/",
            max_age=max_age,
        )
