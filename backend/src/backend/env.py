from enum import StrEnum

from pydantic import field_validator
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
