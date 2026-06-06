from urllib.parse import urlparse

from pydantic import Field, ValidationInfo, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class SpotifyAuthSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_prefix="SPOTIFY_",
    )

    client_id: str = Field(default="")
    client_secret: str = Field(default="")
    redirect_uri: str = Field(default="")

    authorization_endpoint: str = Field(
        default="https://accounts.spotify.com/authorize",
    )
    token_endpoint: str = Field(
        default="https://accounts.spotify.com/api/token",
    )
    userinfo_endpoint: str = Field(
        default="https://api.spotify.com/v1/me",
    )
    state_cookie_name: str = "spotify_oauth_state"
    login_state_cookie_name: str = "spotify_login_state"
    token_encryption_key: str = Field(default="")

    def validate_redirect_host(self, frontend_base_url: str) -> None:
        redirect_host = urlparse(self.redirect_uri).hostname
        frontend_host = urlparse(frontend_base_url).hostname
        if (
            redirect_host
            and frontend_host
            and redirect_host.lower() != frontend_host.lower()
        ):
            raise ValueError(
                "SPOTIFY_REDIRECT_URI host must match frontend_base_url host "
                "so access cookies are sent on /auth/spotify/callback"
            )

    @field_validator("client_id", "client_secret", "redirect_uri")
    @classmethod
    def validate_required_values(cls, value: str, info: ValidationInfo) -> str:
        normalized = value.strip()
        if not normalized:
            if info.field_name == "client_id":
                raise ValueError("Spotify client ID is not configured")
            if info.field_name == "client_secret":
                raise ValueError("Spotify client secret is not configured")
            raise ValueError("Spotify redirect URI is not configured")
        return normalized

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
