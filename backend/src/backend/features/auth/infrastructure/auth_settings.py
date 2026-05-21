from enum import StrEnum

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class _JwtAlgorithm(StrEnum):
    HS256 = "HS256"
    RS256 = "RS256"


class _CookieSameSite(StrEnum):
    STRICT = "strict"
    LAX = "lax"
    NONE = "none"


class GoogleAuthSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_prefix="GOOGLE_",
    )

    client_id: str = Field(
        default="",
        validation_alias=AliasChoices("GOOGLE_CLIENT_ID", "google_client_id"),
    )
    client_secret: str = Field(
        default="",
        validation_alias=AliasChoices(
            "GOOGLE_CLIENT_SECRET",
            "google_client_secret",
        ),
    )
    redirect_uri: str = Field(
        default="",
        validation_alias=AliasChoices("GOOGLE_REDIRECT_URI", "google_redirect_uri"),
    )
    authorization_endpoint: str = Field(
        default="https://accounts.google.com/o/oauth2/v2/auth",
        validation_alias=AliasChoices(
            "GOOGLE_AUTHORIZATION_ENDPOINT",
            "google_authorization_endpoint",
        ),
    )
    scope: str = Field(
        default="openid email profile",
        validation_alias=AliasChoices("GOOGLE_SCOPE", "google_scope"),
    )
    token_endpoint: str = Field(
        default="https://oauth2.googleapis.com/token",
        validation_alias=AliasChoices(
            "GOOGLE_TOKEN_ENDPOINT",
            "google_token_endpoint",
        ),
    )
    userinfo_endpoint: str = Field(
        default="https://openidconnect.googleapis.com/v1/userinfo",
        validation_alias=AliasChoices(
            "GOOGLE_USERINFO_ENDPOINT",
            "google_userinfo_endpoint",
        ),
    )

    @field_validator(
        "redirect_uri",
        "authorization_endpoint",
        "token_endpoint",
        "userinfo_endpoint",
    )
    @classmethod
    def validate_google_urls(cls, v: str) -> str:
        if v and not v.startswith(("http://", "https://")):
            raise ValueError("Google URLs must start with http:// or https://")
        return v.rstrip("/") if v else v


class AuthSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    frontend_base_url: str = "http://localhost:5173"

    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: _JwtAlgorithm = _JwtAlgorithm.HS256
    jwt_access_token_expire_minutes: int = 60 * 24
    jwt_refresh_token_expire_days: int = 7

    access_token_cookie_name: str = "access_token"
    jwt_refresh_token_cookie_name: str = "refresh_token"
    oauth_state_cookie_name: str = "oauth_state"
    spotify_oauth_state_cookie_name: str = "spotify_oauth_state"
    oauth_state_ttl_seconds: int = 60 * 10
    spotify_token_encryption_key: str = ""

    cookie_samesite_dev: _CookieSameSite = _CookieSameSite.LAX
    cookie_samesite_prod: _CookieSameSite = _CookieSameSite.STRICT

    @field_validator("frontend_base_url")
    @classmethod
    def validate_frontend_url(cls, v: str) -> str:
        if not v.startswith(("http://", "https://")):
            raise ValueError("Frontend URL must start with http:// or https://")
        return v.rstrip("/")

    @property
    def allowed_origins(self) -> list[str]:
        return [self.frontend_base_url]


class SpotifyAuthSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_prefix="SPOTIFY_",
    )

    client_id: str = Field(
        default="",
        validation_alias=AliasChoices("SPOTIFY_CLIENT_ID", "spotify_client_id"),
    )
    client_secret: str = Field(
        default="",
        validation_alias=AliasChoices(
            "SPOTIFY_CLIENT_SECRET",
            "spotify_client_secret",
        ),
    )
    redirect_uri: str = Field(
        default="",
        validation_alias=AliasChoices("SPOTIFY_REDIRECT_URI", "spotify_redirect_uri"),
    )
    authorization_endpoint: str = Field(
        default="https://accounts.spotify.com/authorize",
    )
    token_endpoint: str = Field(
        default="https://accounts.spotify.com/api/token",
    )
    userinfo_endpoint: str = Field(
        default="https://api.spotify.com/v1/me",
    )
    scope: str = Field(
        default=(
            "user-read-email "
            "streaming "
            "user-read-private "
            "playlist-modify-private playlist-modify-public"
        ),
    )

    @field_validator(
        "redirect_uri",
        "authorization_endpoint",
        "token_endpoint",
        "userinfo_endpoint",
    )
    @classmethod
    def validate_spotify_urls(cls, v: str) -> str:
        if v and not v.startswith(("http://", "https://")):
            raise ValueError("Spotify URLs must start with http:// or https://")
        return v.rstrip("/") if v else v
