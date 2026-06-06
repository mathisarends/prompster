from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class StripePaymentSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="STRIPE_",
        extra="ignore",
    )

    secret_key: str = Field(default="")
    webhook_secret: str = Field(default="")
    api_base_url: str = "https://api.stripe.com"
    checkout_product_name: str = "Prompster"
    webhook_tolerance_seconds: int = Field(default=300, ge=0)

    @field_validator("secret_key", "webhook_secret")
    @classmethod
    def validate_required_secrets(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Stripe payment credentials are not configured")
        return normalized

    @field_validator("api_base_url")
    @classmethod
    def validate_api_base_url(cls, value: str) -> str:
        if not value.startswith(("http://", "https://")):
            raise ValueError("Stripe API base URL must start with http:// or https://")
        return value.rstrip("/")
