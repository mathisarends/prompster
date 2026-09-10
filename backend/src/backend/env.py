import logging
from enum import StrEnum
from typing import Literal

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class _EnvironmentMode(StrEnum):
    DEV = "dev"
    PROD = "prod"


_LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


class EnvSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    env: _EnvironmentMode = _EnvironmentMode.DEV
    frontend_base_url: str = "http://127.0.0.1:5173"

    @property
    def is_dev(self) -> bool:
        return self.env == _EnvironmentMode.DEV

    @property
    def is_prod(self) -> bool:
        return self.env == _EnvironmentMode.PROD

    @property
    def allowed_origins(self) -> list[str]:
        return [self.frontend_base_url]

    @field_validator("frontend_base_url")
    @classmethod
    def validate_frontend_url(cls, value: str) -> str:
        if not value.startswith(("http://", "https://")):
            raise ValueError("Frontend URL must start with http:// or https://")
        return value.rstrip("/")


class LoggingLevelSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    env: _EnvironmentMode = _EnvironmentMode.DEV
    log_level: _LogLevel | None = Field(
        default=None,
        validation_alias=AliasChoices("LOG_LEVEL", "log_level"),
    )

    @property
    def is_dev(self) -> bool:
        return self.env == _EnvironmentMode.DEV

    @property
    def effective_log_level(self) -> int:
        log_level = self.log_level or ("DEBUG" if self.is_dev else "INFO")
        return logging.getLevelNamesMapping()[log_level]

    @field_validator("log_level", mode="before")
    @classmethod
    def validate_log_level(cls, value: str | None) -> str | None:
        if value is None:
            return None

        normalized = str(value).strip().upper()
        if not normalized:
            return None
        return normalized


class RateLimitSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    agent_message_daily_limit: int = 50
