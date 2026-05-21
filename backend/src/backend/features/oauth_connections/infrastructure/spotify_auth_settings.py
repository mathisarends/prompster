from pydantic import Field, field_validator
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
    token_encryption_key: str = Field(default="")

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
