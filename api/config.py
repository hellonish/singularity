from __future__ import annotations

from pydantic import AliasChoices, Field
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
    environment: str = Field(default="development", validation_alias=AliasChoices("SINGULARITY_ENVIRONMENT", "ENVIRONMENT"))
    database_url: str = Field(default="sqlite+aiosqlite:///./singularity.db", validation_alias=AliasChoices("SINGULARITY_DATABASE_URL", "DATABASE_URL"))
    auto_create_schema: bool = True
    storage_backend: str = "local"
    storage_root: str = "./data/objects"
    chat_messages_per_second: int = 3
    chats_per_second: int = 3
    reports_per_second: int = 1
    research_runs_per_hour: int = 3
    credential_encryption_key: str | None = Field(default=None, validation_alias=AliasChoices("SINGULARITY_CREDENTIAL_ENCRYPTION_KEY", "LLM_CREDENTIALS_ENCRYPTION_KEY"))
    groq_fallback_model: str = "openai/gpt-oss-20b"
    deepseek_fallback_model: str = "deepseek-v4-flash"
    openrouter_fallback_model: str = "openai/gpt-4.1-mini"
    sse_dummy_delay_seconds: float = 0.15
    redis_url: str = Field(default="redis://localhost:6379", validation_alias=AliasChoices("SINGULARITY_REDIS_URL", "REDIS_URL"))
    research_worker_enabled: bool = False


settings = Settings()
