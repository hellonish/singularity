from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings for the API v2 foundation.

    The default uses SQLite for local development. The models deliberately avoid
    SQLite-only types, so a PostgreSQL async URL can replace it later.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="SINGULARITY_",
        extra="ignore",
    )

    app_name: str = "Singularity API"
    environment: str = "development"
    database_url: str = "sqlite+aiosqlite:///./singularity.db"
    auto_create_schema: bool = True
    storage_backend: str = "local"
    storage_root: str = "./data/objects"
    chat_messages_per_second: int = 3
    chats_per_second: int = 3
    reports_per_second: int = 1
    credential_encryption_key: str | None = None
    groq_fallback_model: str = "openai/gpt-oss-20b"
    sse_dummy_delay_seconds: float = 0.15


settings = Settings()
