from __future__ import annotations

from contextlib import asynccontextmanager
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api import __version__
from api.config import settings
from api.database import create_schema, engine
from api.logging_config import configure_logging
from api.middleware.rate_limit import ChatReportRateLimitMiddleware
from api.routers import auth, chats, llm, reports, research, storage, users, walkthroughs
from api.schemas import HealthRead
from engine.chat.capability_router import sandbox_enabled, trusted_function_enabled


@asynccontextmanager
async def lifespan(_app: FastAPI):
    configure_logging()
    if settings.auto_create_schema:
        await create_schema()
    yield
    await engine.dispose()


app = FastAPI(
    title=settings.app_name,
    version=__version__,
    description="Portable API v2 foundation for chats, reports, usage, and auth sessions.",
    lifespan=lifespan,
)

app.add_middleware(
    ChatReportRateLimitMiddleware,
    messages_per_second=settings.chat_messages_per_second,
    chats_per_second=settings.chats_per_second,
    reports_per_second=settings.reports_per_second,
    research_runs_per_hour=settings.research_runs_per_hour,
)

if settings.cors_allow_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["Last-Event-ID"],
    )


@app.get("/health", response_model=HealthRead, tags=["system"])
async def health() -> HealthRead:
    master = os.getenv("SINGULARITY_MODAL_ENABLED", "0") == "1"
    return HealthRead(
        status="ok",
        database=settings.database_url.split(":", 1)[0],
        version=__version__,
        modal_enabled=master,
        modal_trusted_function_enabled=trusted_function_enabled(master),
        modal_sandbox_enabled=sandbox_enabled(master),
    )


app.include_router(auth.router)
app.include_router(users.router)
app.include_router(chats.router)
app.include_router(reports.router)
app.include_router(research.router)
app.include_router(storage.router)
app.include_router(llm.router)
app.include_router(walkthroughs.router)
