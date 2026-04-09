from __future__ import annotations

import logging
import logging.config
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from arq import ArqRedis, create_pool
from arq.connections import RedisSettings
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.router import router as auth_router
from api.llm.router import router as llm_router
from api.config import settings
from api.deps import get_db, get_redis, set_redis_pool
from api.middleware.auth import AuthMiddleware
from api.middleware.rate_limit import RateLimitMiddleware
from api.middleware.request_id import RequestIdFilter, RequestIdMiddleware
from api.middleware.usage_emitter import UsageEmitterMiddleware
from api.reports.router import router as reports_router
from api.research.router import router as research_router
from api.threads.router import router as threads_router
from api.users.router import router as users_router
from api.db.models import Base
from api.db.session import engine


def _configure_logging() -> None:
    """
    Set up structured logging.

    - In production: JSON lines via python-json-logger so log aggregators
      (Datadog, CloudWatch, Loki) can parse fields without regex.
    - In development: human-readable format with request_id included.

    The RequestIdFilter is added to the root handler so every log record
    produced during a request carries the request_id field automatically.
    """
    log_level = logging.DEBUG if settings.environment == "development" else logging.INFO

    try:
        from pythonjsonlogger import jsonlogger

        formatter: logging.Formatter = jsonlogger.JsonFormatter(
            fmt="%(asctime)s %(levelname)s %(name)s %(request_id)s %(message)s",
            rename_fields={"asctime": "timestamp", "levelname": "level"},
        )
    except ImportError:
        # Fall back to plain text if python-json-logger isn't installed.
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s request_id=%(request_id)s — %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    handler.addFilter(RequestIdFilter())

    root = logging.getLogger()
    root.setLevel(log_level)
    # Replace any handlers added by uvicorn/gunicorn so our format wins.
    root.handlers = [handler]


_configure_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # ------------------------------------------------------------------ startup
    logger.info("Starting Singularity API — environment: %s", settings.environment)

    # In development: auto-create all tables.
    # In production Alembic migrations are the sole schema authority.
    if settings.environment == "development":
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables ensured (dev mode)")

    # Initialise ARQ Redis pool.
    # ArqRedis extends redis.asyncio.Redis, so all standard commands
    # (ping, publish, subscribe) plus .enqueue_job() are available.
    redis_pool: ArqRedis = await create_pool(RedisSettings.from_dsn(settings.redis_url))
    set_redis_pool(redis_pool)
    logger.info("ARQ Redis pool initialised")

    # Initialise Sentry if configured
    if settings.sentry_dsn:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            environment=settings.environment,
            integrations=[FastApiIntegration(), SqlalchemyIntegration()],
            traces_sample_rate=0.2,
        )
        logger.info("Sentry initialised")

    yield

    # ----------------------------------------------------------------- shutdown
    logger.info("Shutting down Singularity API")
    await redis_pool.aclose()
    await engine.dispose()
    logger.info("Connections closed")


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Singularity API",
    version="1.0.0",
    description="AI-powered research platform — backend API",
    lifespan=lifespan,
    docs_url="/docs" if settings.environment == "development" else None,
    redoc_url="/redoc" if settings.environment == "development" else None,
)

# ---------------------------------------------------------------------------
# Middleware stack  (add_middleware applies in reverse — last-added runs first)
# ---------------------------------------------------------------------------

# Innermost (runs closest to route handlers)
# Execution order (reverse of add order): RequestId → Auth → RateLimit → UsageEmitter
# RequestId runs first so every subsequent middleware and handler has request_id available.
# Auth must run before RateLimit so rate limiting uses per-user keys, not shared IP.
app.add_middleware(UsageEmitterMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(AuthMiddleware)
app.add_middleware(RequestIdMiddleware)

# CORS — must wrap everything.
# In development, allow any localhost / 127.0.0.1 port so PUT (e.g. BYOK keys) works when the
# Next app runs on a non-3000 port or the user opens 127.0.0.1 vs localhost.
_cors_kw: dict = {
    "allow_credentials": True,
    "allow_methods": ["*"],
    "allow_headers": ["*"],
}
if settings.environment == "development":
    _cors_kw["allow_origin_regex"] = r"^http://(localhost|127\.0\.0\.1)(:\d+)?$"
else:
    _cors_kw["allow_origins"] = settings.cors_origins
app.add_middleware(CORSMiddleware, **_cors_kw)

# Sentry request monitoring is registered via sentry_sdk.init() during lifespan
# and attaches automatically as ASGI middleware.

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(auth_router, prefix="/api/v1")
app.include_router(research_router, prefix="/api/v1")
app.include_router(reports_router, prefix="/api/v1")
app.include_router(threads_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")
app.include_router(llm_router, prefix="/api/v1")


# ---------------------------------------------------------------------------
# Health / readiness endpoints
# ---------------------------------------------------------------------------


@app.get("/api/health", tags=["ops"])
async def health() -> dict:
    """Lightweight liveness probe — always 200 when the process is up."""
    return {"status": "ok"}


@app.get("/api/ready", tags=["ops"])
async def ready(
    db: AsyncSession = Depends(get_db),
    redis: ArqRedis = Depends(get_redis),
) -> dict:
    """
    Readiness probe — verifies connectivity to PostgreSQL and Redis.

    Returns 200 only when both data stores respond successfully.
    """
    await db.execute(text("SELECT 1"))
    await redis.ping()
    return {"status": "ready"}
