from __future__ import annotations

from typing import Literal

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

    # Database selection. Production defaults to PostgreSQL so the prod
    # environment needs no extra flags. Local development sets
    # ``SINGULARITY_USE_SQLITE=true`` to opt into the SQLite file instead.
    #
    # Precedence (see the ``database_url`` property):
    #   1. an explicit SINGULARITY_DATABASE_URL always wins (full override);
    #   2. else use_sqlite=true  -> the local SQLite file;
    #   3. else                  -> the PostgreSQL URL (the default).
    use_sqlite: bool = Field(default=False, validation_alias=AliasChoices("SINGULARITY_USE_SQLITE", "USE_SQLITE"))
    database_url_override: str | None = Field(default=None, validation_alias=AliasChoices("SINGULARITY_DATABASE_URL", "DATABASE_URL"))
    postgres_url: str = Field(
        default="postgresql+asyncpg://singularity:loremipsum@localhost:5432/singularity",
        validation_alias=AliasChoices("SINGULARITY_POSTGRES_URL", "POSTGRES_URL"),
    )
    sqlite_url: str = Field(
        default="sqlite+aiosqlite:///./singularity.db",
        validation_alias=AliasChoices("SINGULARITY_SQLITE_URL", "SQLITE_URL"),
    )
    auto_create_schema: bool = True
    storage_backend: str = "local"
    storage_root: str = "./data/objects"

    # Supabase Storage exposes an S3-compatible endpoint. When
    # ``storage_backend`` is "s3" these configure the aioboto3 client. The
    # endpoint is the project's Storage S3 URL
    # (https://<project-ref>.supabase.co/storage/v1/s3); credentials are the
    # S3 access key id and secret generated in the Supabase dashboard under
    # Storage → S3 access keys. Region matches the project region.
    s3_bucket: str = Field(default="", validation_alias=AliasChoices("SINGULARITY_S3_BUCKET", "S3_BUCKET"))
    s3_endpoint_url: str | None = Field(default=None, validation_alias=AliasChoices("SINGULARITY_S3_ENDPOINT_URL", "S3_ENDPOINT_URL"))
    s3_region: str = Field(default="us-east-1", validation_alias=AliasChoices("SINGULARITY_S3_REGION", "S3_REGION"))
    s3_access_key_id: str | None = Field(default=None, validation_alias=AliasChoices("SINGULARITY_S3_ACCESS_KEY_ID", "S3_ACCESS_KEY_ID"))
    s3_secret_access_key: str | None = Field(default=None, validation_alias=AliasChoices("SINGULARITY_S3_SECRET_ACCESS_KEY", "S3_SECRET_ACCESS_KEY"))
    # File logging. When ``log_file`` is set, application logs are also written
    # there (in addition to the console). ``log_mode`` controls verbosity of the
    # step logger used across the chat and research flows:
    #   "full"  – every step plus its inputs and outputs (verbose; may include
    #             user content, so treat the file as sensitive).
    #   "steps" – step boundaries only, no payloads (safe for shared operators).
    # ``log_level`` is the standard threshold for all logging.
    log_file: str | None = Field(default="./logs/singularity.log", validation_alias=AliasChoices("SINGULARITY_LOG_FILE", "LOG_FILE"))
    log_mode: Literal["full", "steps"] = Field(default="steps", validation_alias=AliasChoices("SINGULARITY_LOG_MODE", "LOG_MODE"))
    log_level: str = Field(default="INFO", validation_alias=AliasChoices("SINGULARITY_LOG_LEVEL", "LOG_LEVEL"))
    log_max_bytes: int = 10 * 1024 * 1024
    log_backup_count: int = 5

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
    def database_url(self) -> str:
        """Effective async database URL.

        An explicit ``SINGULARITY_DATABASE_URL`` overrides everything; otherwise
        SQLite is used only when ``SINGULARITY_USE_SQLITE`` is set, and PostgreSQL
        is the default so production requires no flag.
        """
        if self.database_url_override:
            return self.database_url_override
        return self.sqlite_url if self.use_sqlite else self.postgres_url

    @property
    def cors_allow_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allow_origins_raw.split(",") if origin.strip()]


settings = Settings()
