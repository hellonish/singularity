from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from api import __version__
from api.config import settings
from api.database import create_schema, engine
from api.middleware.rate_limit import ChatReportRateLimitMiddleware
from api.routers import chats, llm, reports, research, storage, users
from api.schemas import HealthRead


@asynccontextmanager
async def lifespan(_app: FastAPI):
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


@app.get("/health", response_model=HealthRead, tags=["system"])
async def health() -> HealthRead:
    return HealthRead(status="ok", database=settings.database_url.split(":", 1)[0], version=__version__)


app.include_router(users.router)
app.include_router(chats.router)
app.include_router(reports.router)
app.include_router(research.router)
app.include_router(storage.router)
app.include_router(llm.router)
