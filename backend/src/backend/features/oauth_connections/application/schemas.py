from typing import Self

from pydantic import BaseModel, model_validator


class SpotifyTokens(BaseModel):
    access_token: str
    refresh_token: str | None = None
    expires_in: int
    scope: str
    token_type: str


class SpotifyAuthorizationRequest(BaseModel):
    authorization_url: str
    state: str


class SpotifyCallbackResult(BaseModel):
    succeeded: bool
    error_reason: str | None = None

    @classmethod
    def success(cls) -> Self:
        return cls(succeeded=True)

    @classmethod
    def error(cls, *, reason: str) -> Self:
        return cls(succeeded=False, error_reason=reason)

    @model_validator(mode="after")
    def validate_consistency(self) -> Self:
        if self.succeeded and self.error_reason is not None:
            raise ValueError("Successful callback result must not include an error")
        if not self.succeeded and self.error_reason is None:
            raise ValueError("Failed callback result must include an error reason")
        return self


class SpotifyAccessToken(BaseModel):
    access_token: str
    expires_in: int
    scope: str


class SpotifyUserProfile(BaseModel):
    spotify_user_id: str
    is_premium: bool
    display_name: str | None = None
    profile_image_url: str | None = None
