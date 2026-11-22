from pydantic import AliasChoices, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


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
    client_secret: SecretStr = Field(
        default=SecretStr(""),
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
        default="openid profile",
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
    state_cookie_name: str = "oauth_state"

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
