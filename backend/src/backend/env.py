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


class LLMCredentials(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    openai_api_key: str
