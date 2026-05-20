from enum import StrEnum

from pydantic_settings import BaseSettings, SettingsConfigDict


class _EnvironmentMode(StrEnum):
    DEV = "dev"
    PROD = "prod"


class EnvSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    env: _EnvironmentMode = _EnvironmentMode.DEV

    allowed_origins: set[str] = set()

    @property
    def is_dev(self) -> bool:
        return self.env == _EnvironmentMode.DEV

    @property
    def is_prod(self) -> bool:
        return self.env == _EnvironmentMode.PROD


# TODO: Actually use this and block routes if they do not support it
class FeatureToggleSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    enable_spotify_sync: bool = False
