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

    # Real-inference smoke testing only. When enabled, a research run may pass
    # ``test_mode: true`` to force the minimal single-node profile (one real
    # search + one real fetch). Off by default; both this flag and the per-
    # request field are required, so it can never engage in normal operation.
    research_test_mode: bool = Field(default=False, validation_alias=AliasChoices("SINGULARITY_RESEARCH_TEST_MODE", "RESEARCH_TEST_MODE"))

    # Authentication. "bearer" (default) requires a signed access JWT; "header"
    # preserves the temporary X-User-ID identity boundary for local curl and the
    # deterministic test suite. Real auth needs google_client_id + jwt_secret.
    auth_mode: str = Field(default="bearer", validation_alias=AliasChoices("SINGULARITY_AUTH_MODE", "AUTH_MODE"))
    google_client_id: str | None = Field(default=None, validation_alias=AliasChoices("SINGULARITY_GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_ID"))
    jwt_secret: str | None = Field(default=None, validation_alias=AliasChoices("SINGULARITY_JWT_SECRET", "JWT_SECRET"))
    jwt_algorithm: str = "HS256"
    access_token_ttl_seconds: int = 15 * 60
    refresh_token_ttl_seconds: int = 30 * 24 * 60 * 60

    # Empty by default: CORS is inert until an origin is configured, so it does
    # not presume any particular client. A comma-separated env string is kept as
    # a plain string here (pydantic-settings would otherwise JSON-parse a list
    # field) and split by ``cors_allow_origins``.
    cors_allow_origins_raw: str = Field(default="", validation_alias=AliasChoices("SINGULARITY_CORS_ALLOW_ORIGINS", "CORS_ALLOW_ORIGINS"))

    @property
    def cors_allow_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allow_origins_raw.split(",") if origin.strip()]


settings = Settings()
