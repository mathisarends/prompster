from pydantic import BaseModel, Field, field_validator


class EmailPasswordRequest(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def email_must_be_valid(cls, value: str) -> str:
        if "@" not in value or "." not in value.split("@")[-1]:
            raise ValueError("Ungültige E-Mail-Adresse")
        return value


class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: str
    password: str = Field(min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def email_must_be_valid(cls, value: str) -> str:
        if "@" not in value or "." not in value.split("@")[-1]:
            raise ValueError("Ungültige E-Mail-Adresse")
        return value
