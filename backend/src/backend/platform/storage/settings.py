from pydantic_settings import BaseSettings, SettingsConfigDict


class S3StorageCredentials(BaseSettings):
    endpoint_url: str
    access_key: str
    secret_key: str
    public_endpoint_url: str | None = None

    model_config = SettingsConfigDict(env_prefix="MINIO_")


class StorageSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    storage_bucket_name: str
