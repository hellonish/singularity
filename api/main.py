from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from arq import ArqRedis, create_pool
from arq.connections import RedisSettings
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.router import router as auth_router
from api.config import settings
from api.deps import get_db, get_redis, set_redis_pool
from api.middleware.auth import AuthMiddleware
from api.middleware.rate_limit import RateLimitMiddleware
from api.middleware.request_id import RequestIDMiddleware
from api.middleware.usage_emitter import UsageEmitterMiddleware
from api.reports.router import router as reports_router
from api.research.router import router as research_router
from api.threads.router import router as threads_router
from api.users.router import router as users_router
from db.models import Base
from db.session import engine

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
app.add_middleware(UsageEmitterMiddleware)
app.add_middleware(AuthMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(RequestIDMiddleware)

# CORS — must wrap everything
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)

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
