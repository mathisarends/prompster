import asyncio

import resend
from pydantic import AliasChoices, Field, ValidationInfo, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from backend.shared.email import EmailMessage, EmailSender


class ResendEmailSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    api_key: str = Field(
        validation_alias=AliasChoices("RESEND_API_KEY", "resend_api_key")
    )
    default_from_email: str = Field(
        default="noreply@yourdomain.com",
        validation_alias=AliasChoices("RESEND_FROM_EMAIL", "resend_from_email"),
    )

    @field_validator("api_key", "default_from_email")
    @classmethod
    def validate_non_empty_values(cls, value: str, info: ValidationInfo) -> str:
        normalized = value.strip()
        if normalized:
            return normalized

        if info.field_name == "api_key":
            raise ValueError("Resend API key is not configured")
        raise ValueError("Resend sender email is not configured")


class ResendEmailSender(EmailSender):
    def __init__(self, settings: ResendEmailSettings) -> None:
        resend.api_key = settings.api_key
        self._default_from_email = settings.default_from_email

    async def send(self, message: EmailMessage) -> None:
        await asyncio.to_thread(
            resend.Emails.send,
            {
                "from": message.from_email or self._default_from_email,
                "to": message.to,
                "subject": message.subject,
                "html": message.html,
            },
        )
