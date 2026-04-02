"""
User service layer — profile, stats, and usage analytics.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from api.config import settings
from db.models import Report, UsageEvent, User


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def get_user_profile(db: AsyncSession, user_id: uuid.UUID) -> User:
    result = await db.execute(select(User).where(User.id == user_id))
    user: User | None = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


async def compute_stats(db: AsyncSession, user_id: uuid.UUID) -> dict:
    """Compute aggregate usage statistics for the user."""
    now = _now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = now - timedelta(days=now.weekday())
    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)

    # Total reports
    total_reports_result = await db.execute(
        select(func.count(Report.id)).where(Report.user_id == user_id)
    )
    total_reports: int = total_reports_result.scalar() or 0

    # Reports this week
    reports_week_result = await db.execute(
        select(func.count(Report.id)).where(
            Report.user_id == user_id,
            Report.created_at >= week_start,
        )
    )
    reports_this_week: int = reports_week_result.scalar() or 0

    # Token usage (prompt + completion) today
    tokens_today_result = await db.execute(
        select(
            func.coalesce(func.sum(UsageEvent.prompt_tokens), 0)
            + func.coalesce(func.sum(UsageEvent.completion_tokens), 0)
        ).where(
            UsageEvent.user_id == user_id,
            UsageEvent.created_at >= today_start,
        )
    )
    tokens_today: int = int(tokens_today_result.scalar() or 0)

    # Total tokens and cost
    totals_result = await db.execute(
        select(
            func.coalesce(func.sum(UsageEvent.prompt_tokens), 0)
            + func.coalesce(func.sum(UsageEvent.completion_tokens), 0),
            func.coalesce(func.sum(UsageEvent.cost_usd), 0),
        ).where(UsageEvent.user_id == user_id)
    )
    row = totals_result.one()
    total_tokens: int = int(row[0] or 0)
    total_cost_usd: Decimal = row[1] or Decimal("0")

    # Average report strength
    avg_strength_result = await db.execute(
        select(func.avg(Report.strength)).where(Report.user_id == user_id)
    )
    avg_strength: float = float(avg_strength_result.scalar() or 5.0)

    # Favorite model (most tokens used)
    fav_model_result = await db.execute(
        select(UsageEvent.model, func.sum(UsageEvent.prompt_tokens + UsageEvent.completion_tokens).label("total"))
        .where(UsageEvent.user_id == user_id, UsageEvent.model.isnot(None))
        .group_by(UsageEvent.model)
        .order_by(text("total DESC"))
        .limit(1)
    )
    fav_row = fav_model_result.first()
    favorite_model: Optional[str] = fav_row[0] if fav_row else None

    # Most active hour
    active_hour_result = await db.execute(
        select(
            func.extract("hour", UsageEvent.created_at).label("h"),
            func.count(UsageEvent.id).label("cnt"),
        )
        .where(UsageEvent.user_id == user_id)
        .group_by(text("h"))
        .order_by(text("cnt DESC"))
        .limit(1)
    )
    hour_row = active_hour_result.first()
    most_active_hour: Optional[int] = int(hour_row[0]) if hour_row else None

    # Streak: count consecutive days with usage ending today
    streak = await _compute_streak(db, user_id)

    # Get user's daily budget
    user_result = await db.execute(select(User).where(User.id == user_id))
    user: User | None = user_result.scalar_one_or_none()
    daily_budget = user.daily_token_budget if user else settings.default_daily_token_budget

    return {
        "total_reports": total_reports,
        "total_tokens": total_tokens,
        "total_cost_usd": total_cost_usd,
        "reports_this_week": reports_this_week,
        "tokens_today": tokens_today,
        "tokens_remaining_today": max(0, daily_budget - tokens_today),
        "streak_days": streak,
        "avg_report_strength": round(avg_strength, 1),
        "favorite_model": favorite_model,
        "most_active_hour": most_active_hour,
    }


async def _compute_streak(db: AsyncSession, user_id: uuid.UUID) -> int:
    """Compute the current daily usage streak."""
    now = _now()
    streak = 0
    for days_ago in range(365):  # Max 1 year streak
        day = now - timedelta(days=days_ago)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)

        result = await db.execute(
            select(func.count(UsageEvent.id)).where(
                UsageEvent.user_id == user_id,
                UsageEvent.created_at >= day_start,
                UsageEvent.created_at < day_end,
            )
        )
        count: int = result.scalar() or 0
        if count > 0:
            streak += 1
        else:
            # Allow today to have no activity yet
            if days_ago == 0:
                continue
            break
    return streak


async def get_usage_series(
    db: AsyncSession,
    user_id: uuid.UUID,
    days: int = 30,
) -> dict:
    """Get daily usage time series."""
    now = _now()
    start = now - timedelta(days=days)
    start_date = start.replace(hour=0, minute=0, second=0, microsecond=0)

    result = await db.execute(
        select(
            func.date_trunc("day", UsageEvent.created_at).label("day"),
            func.sum(
                func.coalesce(UsageEvent.prompt_tokens, 0)
                + func.coalesce(UsageEvent.completion_tokens, 0)
            ).label("tokens"),
            func.sum(UsageEvent.cost_usd).label("cost"),
        )
        .where(
            UsageEvent.user_id == user_id,
            UsageEvent.created_at >= start_date,
        )
        .group_by(text("day"))
        .order_by(text("day"))
    )
    rows = result.all()

    # Count reports per day
    report_result = await db.execute(
        select(
            func.date_trunc("day", Report.created_at).label("day"),
            func.count(Report.id).label("count"),
        )
        .where(
            Report.user_id == user_id,
            Report.created_at >= start_date,
        )
        .group_by(text("day"))
    )
    report_counts = {r[0].strftime("%Y-%m-%d"): r[1] for r in report_result.all()}

    series = []
    total_tokens = 0
    total_cost = Decimal("0")
    for row in rows:
        date_str = row[0].strftime("%Y-%m-%d")
        tokens = int(row[1] or 0)
        cost = row[2] or Decimal("0")
        total_tokens += tokens
        total_cost += cost
        series.append({
            "date": date_str,
            "tokens": tokens,
            "cost_usd": cost,
            "reports": report_counts.get(date_str, 0),
        })

    return {
        "series": series,
        "total_tokens": total_tokens,
        "total_cost_usd": total_cost,
    }


async def get_model_breakdown(db: AsyncSession, user_id: uuid.UUID) -> dict:
    """Get token and cost breakdown by model."""
    result = await db.execute(
        select(
            UsageEvent.model,
            func.sum(
                func.coalesce(UsageEvent.prompt_tokens, 0)
                + func.coalesce(UsageEvent.completion_tokens, 0)
            ).label("tokens"),
            func.sum(UsageEvent.cost_usd).label("cost"),
        )
        .where(UsageEvent.user_id == user_id, UsageEvent.model.isnot(None))
        .group_by(UsageEvent.model)
        .order_by(text("tokens DESC"))
    )
    rows = result.all()

    total_tokens = sum(int(r[1] or 0) for r in rows)
    breakdown = []
    for row in rows:
        model_tokens = int(row[1] or 0)
        pct = int((model_tokens / total_tokens * 100) if total_tokens > 0 else 0)
        breakdown.append({
            "model": row[0],
            "tokens": model_tokens,
            "cost_usd": row[2] or Decimal("0"),
            "pct": pct,
        })

    return {"breakdown": breakdown}


async def get_device_breakdown(db: AsyncSession, user_id: uuid.UUID) -> dict:
    """Get device, OS, and browser breakdown."""
    # Devices
    device_result = await db.execute(
        select(UsageEvent.device_type, func.count(UsageEvent.id).label("count"))
        .where(UsageEvent.user_id == user_id, UsageEvent.device_type.isnot(None))
        .group_by(UsageEvent.device_type)
        .order_by(text("count DESC"))
    )
    devices = [{"device_type": r[0], "count": r[1]} for r in device_result.all()]

    # OS
    os_result = await db.execute(
        select(UsageEvent.os, func.count(UsageEvent.id).label("count"))
        .where(UsageEvent.user_id == user_id, UsageEvent.os.isnot(None))
        .group_by(UsageEvent.os)
        .order_by(text("count DESC"))
    )
    os_list = [{"os": r[0], "count": r[1]} for r in os_result.all()]

    # Browsers
    browser_result = await db.execute(
        select(UsageEvent.browser, func.count(UsageEvent.id).label("count"))
        .where(UsageEvent.user_id == user_id, UsageEvent.browser.isnot(None))
        .group_by(UsageEvent.browser)
        .order_by(text("count DESC"))
    )
    browsers = [{"browser": r[0], "count": r[1]} for r in browser_result.all()]

    return {"devices": devices, "os": os_list, "browsers": browsers}
