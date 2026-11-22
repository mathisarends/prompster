from pydantic import AliasChoices, BaseModel, Field, field_validator


class SpotifyIdentity(BaseModel):
    subject: str
    display_name: str | None = None
    profile_image_url: str | None = None


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
