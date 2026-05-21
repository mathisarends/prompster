from pydantic_settings import BaseSettings, SettingsConfigDict


class OAuthStateSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_prefix="OAUTH_STATE_",
    )

    ttl_seconds: int = 60 * 10
