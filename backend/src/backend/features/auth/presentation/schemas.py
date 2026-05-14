from pydantic import BaseModel, field_validator


class EmailPasswordRequest(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def email_must_be_valid(cls, value: str) -> str:
        if "@" not in value or "." not in value.split("@")[-1]:
            raise ValueError("Ungültige E-Mail-Adresse")
        return value
