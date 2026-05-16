from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import AliasChoices, BaseModel, Field, field_validator


class AuthSession(BaseModel):
    jwt_token: str
    refresh_token: str


class GoogleIdentity(BaseModel):
    subject: str = Field(validation_alias=AliasChoices("subject", "sub"))
    email: str
    name: str | None = None
    email_verified: bool = False

    @field_validator("subject")
    @classmethod
    def normalize_subject(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("subject must not be empty")
        return normalized

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not normalized:
            raise ValueError("email must not be empty")
        return normalized

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str | None) -> str | None:
        if value is None:
            return None

        normalized = value.strip()
        return normalized or None


class TokenType(StrEnum):
    ACCESS = "access"
    REFRESH = "refresh"


class TokenPayload(BaseModel):
    user_id: UUID
    email: str | None = None
    expires_at: datetime
