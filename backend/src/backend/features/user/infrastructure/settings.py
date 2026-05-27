from pydantic_settings import BaseSettings, SettingsConfigDict


class UserMessageQuotaSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AGENT_QUOTA_")

    daily_message_limit: int = 50
