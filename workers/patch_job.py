"""
ARQ worker task — applies a patch edit to a report section.

Flow:
1. Load the target report version + content
2. Call the patch service (LLM-driven edit)
3. Create a new report version with the patched content
4. Publish SSE event on completion
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.llm_credentials_service import get_decrypted_provider_key
from api.db.models import Report, ReportVersion
from api.db.session import AsyncSessionLocal
from workers.research_job import _publish_event, create_report_version

logger = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def run_patch_job(
    ctx: dict,
    report_id: str,
    version_num: int,
    user_id: str,
    selected_text: str,
    instruction: str,
    expected_etag: str,
) -> dict:
    """
    Apply a patch to a specific section of a report version.

    Steps:
    1. Load the target version and verify ETag (optimistic lock)
    2. Load full content
    3. Apply the patch via LLM
    4. Create a new version with the patched content
    5. Publish completion event

    Returns a dict with the new version info.
    """
    redis = ctx["redis"]

    async with AsyncSessionLocal() as db:
        # Load the target version
        result = await db.execute(
            select(ReportVersion).where(
                ReportVersion.report_id == uuid.UUID(report_id),
                ReportVersion.version_num == version_num,
            )
        )
        version: ReportVersion | None = result.scalar_one_or_none()
        if version is None:
            raise ValueError(f"Version {version_num} not found for report {report_id}")

        # Optimistic lock check
        if version.content_hash != expected_etag:
            raise ValueError("Content has been modified — ETag mismatch")

        # Load content
        from api.reports.service import load_content
        content = await load_content(version)

        grok_key = await get_decrypted_provider_key(db, uuid.UUID(user_id), "grok")
        if not grok_key:
            raise ValueError(
                "Add your xAI (Grok) API key in Profile → LLM keys to apply patches."
            )

        # Apply the patch
        try:
            from patch.service import apply_patch
            patched_content = await apply_patch(
                full_content=content,
                selected_text=selected_text,
                instruction=instruction,
                api_key=grok_key,
            )
        except Exception as exc:
            logger.error("Patch failed for report %s v%d: %s", report_id, version_num, exc)
            raise

        # Create new version
        new_version = await create_report_version(
            db,
            uuid.UUID(report_id),
            patched_content,
            patch_instruction=instruction,
        )

        logger.info(
            "Patch applied: report %s v%d → v%d",
            report_id, version_num, new_version.version_num,
        )

        # Publish event on the report's job channel (if any active job)
        await _publish_event(
            redis,
            report_id,
            "patch_done",
            {
                "report_id": report_id,
                "old_version": version_num,
                "new_version": new_version.version_num,
                "new_etag": new_version.content_hash,
                "char_count": new_version.char_count,
            },
        )

        return {
            "new_version_num": new_version.version_num,
            "etag": new_version.content_hash,
            "char_count": new_version.char_count,
        }
