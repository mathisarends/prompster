from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    # Lets the app be imported without configuration, for tests and codegen.
    # Deployments and Compose set DB_URI. Canon selects asyncpg for postgresql://.
    db_uri: str = "postgresql+asyncpg://localhost:5432/prompster"
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_pool_pre_ping: bool = True
    db_pool_recycle: int = 1800
