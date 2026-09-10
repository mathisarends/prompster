from datetime import datetime
from enum import StrEnum
from typing import Self
from uuid import UUID

from pydantic import AliasChoices, BaseModel, Field, field_validator, model_validator


class AuthSession(BaseModel):
    access_token: str
    refresh_token: str


class GoogleAuthorizationRequest(BaseModel):
    authorization_url: str
    state: str


class SpotifyLoginAuthorizationRequest(BaseModel):
    authorization_url: str
    state: str


class GoogleCallbackResult(BaseModel):
    succeeded: bool
    session: AuthSession | None = None
    error_reason: str | None = None

    @classmethod
    def success(cls, *, session: AuthSession) -> Self:
        return cls(succeeded=True, session=session)

    @classmethod
    def error(cls, *, reason: str) -> Self:
        return cls(succeeded=False, error_reason=reason)

    @model_validator(mode="after")
    def validate_consistency(self) -> Self:
        if self.succeeded:
            if self.session is None or self.error_reason is not None:
                msg = "Successful callback result must include only a session"
                raise ValueError(msg)
        elif self.error_reason is None:
            msg = "Failed callback result must include an error reason"
            raise ValueError(msg)

        return self


class SpotifyLoginCallbackResult(BaseModel):
    succeeded: bool
    session: AuthSession | None = None
    error_reason: str | None = None

    @classmethod
    def success(cls, *, session: AuthSession) -> Self:
        return cls(succeeded=True, session=session)

    @classmethod
    def error(cls, *, reason: str) -> Self:
        return cls(succeeded=False, error_reason=reason)

    @model_validator(mode="after")
    def validate_consistency(self) -> Self:
        if self.succeeded:
            if self.session is None or self.error_reason is not None:
                msg = "Successful callback result must include only a session"
                raise ValueError(msg)
        elif self.error_reason is None:
            msg = "Failed callback result must include an error reason"
            raise ValueError(msg)
        return self


class GoogleIdentity(BaseModel):
    subject: str = Field(validation_alias=AliasChoices("subject", "sub"))
    name: str | None = None
    profile_image_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("profile_image_url", "picture"),
    )

    @field_validator("subject")
    @classmethod
    def normalize_subject(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("subject must not be empty")
        return normalized

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str | None) -> str | None:
        if value is None:
            return None

        normalized = value.strip()
        return normalized or None

    @field_validator("profile_image_url")
    @classmethod
    def normalize_profile_image_url(cls, value: str | None) -> str | None:
        if value is None:
            return None

        normalized = value.strip()
        return normalized or None


class TokenType(StrEnum):
    ACCESS = "access"
    REFRESH = "refresh"


class TokenPayload(BaseModel):
    user_id: UUID
    expires_at: datetime
