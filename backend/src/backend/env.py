import logging
from enum import StrEnum

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class _EnvironmentMode(StrEnum):
    DEV = "dev"
    PROD = "prod"


class _LogLevel(StrEnum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class EnvSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    env: _EnvironmentMode = _EnvironmentMode.DEV
    frontend_base_url: str = "http://127.0.0.1:5173"
    log_level: _LogLevel | None = Field(
        default=None,
        validation_alias=AliasChoices("LOG_LEVEL", "log_level"),
    )

    @property
    def is_dev(self) -> bool:
        return self.env == _EnvironmentMode.DEV

    @property
    def is_prod(self) -> bool:
        return self.env == _EnvironmentMode.PROD

    @property
    def allowed_origins(self) -> list[str]:
        return [self.frontend_base_url]

    @property
    def effective_log_level(self) -> int:
        log_level = self.log_level or (
            _LogLevel.DEBUG if self.is_dev else _LogLevel.INFO
        )
        return logging.getLevelNamesMapping()[log_level.value]

    @field_validator("log_level", mode="before")
    @classmethod
    def validate_log_level(cls, value: str | _LogLevel | None) -> str | None:
        if value is None:
            return None

        normalized = str(value).strip().upper()
        if not normalized:
            return None
        return normalized

    @field_validator("frontend_base_url")
    @classmethod
    def validate_frontend_url(cls, value: str) -> str:
        if not value.startswith(("http://", "https://")):
            raise ValueError("Frontend URL must start with http:// or https://")
        return value.rstrip("/")


class RateLimitSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    agent_message_daily_limit: int = 50
