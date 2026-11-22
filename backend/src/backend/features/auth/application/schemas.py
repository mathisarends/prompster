from typing import Self

from pydantic import BaseModel, model_validator

from backend.shared.authentication import AuthSession


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
