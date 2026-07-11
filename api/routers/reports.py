from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.responses import PlainTextResponse, StreamingResponse

from api.config import settings
from api.dependencies import CurrentUserDep, SessionDep
from api.schemas import ReportCreate, ReportRead, ReportVersionCreate, ReportVersionRead
from api.services import reports as report_service
from api.sse import SSE_HEADERS, encode_sse
from api.storage import ObjectStore, get_object_store

router = APIRouter(prefix="/reports", tags=["reports"])
StoreDep = Annotated[ObjectStore, Depends(get_object_store)]


@router.get("", response_model=list[ReportRead])
async def list_reports(session: SessionDep, current_user: CurrentUserDep) -> list[ReportRead]:
    return await report_service.list_reports(session, current_user.id)


@router.post("", response_model=ReportRead, status_code=status.HTTP_201_CREATED)
async def create_report(
    body: ReportCreate,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> ReportRead:
    return await report_service.create_report(session, current_user, body)


@router.get("/{report_id}", response_model=ReportRead)
async def get_report(report_id: str, session: SessionDep, current_user: CurrentUserDep) -> ReportRead:
    return await report_service.get_report(session, current_user.id, report_id)


@router.get("/{report_id}/stream")
async def stream_report(
    report_id: str,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> StreamingResponse:
    """Stream deterministic dummy report sections through the backend SSE contract."""

    report = await report_service.get_report(session, current_user.id, report_id)
    title = report.title or "Untitled report"
    chunks = (
        f"# {title}\n\n",
        "## Summary\n\n",
        "This is dummy report content streamed from the backend.\n",
    )

    async def events() -> AsyncIterator[str]:
        yield encode_sse(
            event="report.started",
            event_id=f"{report.id}:0",
            data={"report_id": report.id, "title": title},
        )
        content = ""
        for index, chunk in enumerate(chunks, start=1):
            if settings.sse_dummy_delay_seconds:
                await asyncio.sleep(settings.sse_dummy_delay_seconds)
            content += chunk
            yield encode_sse(
                event="report.delta",
                event_id=f"{report.id}:{index}",
                data={"report_id": report.id, "index": index - 1, "delta": chunk},
            )
        yield encode_sse(
            event="report.completed",
            event_id=f"{report.id}:{len(chunks) + 1}",
            data={"report_id": report.id, "content": content},
        )

    return StreamingResponse(events(), media_type="text/event-stream", headers=SSE_HEADERS)


@router.get("/{report_id}/versions", response_model=list[ReportVersionRead])
async def list_versions(report_id: str, session: SessionDep, current_user: CurrentUserDep) -> list[ReportVersionRead]:
    report = await report_service.get_report(session, current_user.id, report_id)
    return await report_service.list_versions(session, report)


@router.post("/{report_id}/versions", response_model=ReportVersionRead, status_code=status.HTTP_201_CREATED)
async def create_version(
    report_id: str,
    body: ReportVersionCreate,
    session: SessionDep,
    current_user: CurrentUserDep,
    store: StoreDep,
) -> ReportVersionRead:
    report = await report_service.get_report(session, current_user.id, report_id)
    return await report_service.create_version(session, report, body, store)


@router.get("/{report_id}/versions/{version_id}/content", response_class=PlainTextResponse)
async def read_version_content(
    report_id: str,
    version_id: str,
    session: SessionDep,
    current_user: CurrentUserDep,
    store: StoreDep,
) -> PlainTextResponse:
    report = await report_service.get_report(session, current_user.id, report_id)
    version = await report_service.get_version(session, report, version_id)
    content = await report_service.read_version_content(version, store)
    return PlainTextResponse(content, media_type="text/markdown")
