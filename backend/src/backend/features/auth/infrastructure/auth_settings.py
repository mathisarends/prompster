from enum import StrEnum

from pydantic_settings import BaseSettings, SettingsConfigDict


class _JwtAlgorithm(StrEnum):
    HS256 = "HS256"
    RS256 = "RS256"


class _CookieSameSite(StrEnum):
    STRICT = "strict"
    LAX = "lax"
    NONE = "none"


class AuthSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: _JwtAlgorithm = _JwtAlgorithm.HS256
    jwt_access_token_expire_minutes: int = 60 * 24
    jwt_refresh_token_expire_days: int = 7

    access_token_cookie_name: str = "access_token"
    jwt_refresh_token_cookie_name: str = "refresh_token"

    cookie_samesite_dev: _CookieSameSite = _CookieSameSite.LAX
    cookie_samesite_prod: _CookieSameSite = _CookieSameSite.STRICT
