from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/singularity"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # JWT
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30

    # Google OAuth
    google_client_id: str = ""

    # Blob storage
    blob_store: str = "local"  # "local" | "s3"
    local_blob_dir: str = "./blob_storage"
    s3_bucket: str = ""
    s3_endpoint_url: str = ""
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""

    # Observability
    sentry_dsn: str = ""
    environment: str = "development"

    # CORS / Frontend (browser PUT/DELETE preflight must match the page origin)
    frontend_url: str = "http://localhost:3000"
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    # BYOK: Fernet key (url-safe base64, 32 bytes); empty in dev falls back to JWT-derived key
    llm_credentials_encryption_key: str = ""

    # Quotas
    default_daily_token_budget: int = 1_000_000
    max_concurrent_jobs_per_user: int = 2


settings = Settings()
