import resend

from pydantic import ValidationInfo, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from backend.shared.email import EmailMessage, EmailSender


class ResendEmailSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="RESEND_",
        extra="ignore",
    )

    api_key: str
    from_email: str = "onboarding@resend.dev"

    @field_validator("api_key", "from_email")
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
        self._default_from_email = settings.from_email

    async def send(self, message: EmailMessage) -> None:
        await resend.Emails.send_async(
            {
                "from": message.from_email or self._default_from_email,
                "to": message.to,
                "subject": message.subject,
                "html": message.html,
            }
        )
