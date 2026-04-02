"""Pydantic schemas for the Users / Stats API."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class UserProfile(BaseModel):
    id: UUID
    email: str
    name: Optional[str]
    avatar_url: Optional[str]
    created_at: datetime
    daily_token_budget: int

    model_config = {"from_attributes": True}


class UsageStats(BaseModel):
    total_reports: int
    total_tokens: int
    total_cost_usd: Decimal
    reports_this_week: int
    tokens_today: int
    tokens_remaining_today: int
    streak_days: int
    avg_report_strength: float
    favorite_model: Optional[str]
    most_active_hour: Optional[int]


class UsageSeriesPoint(BaseModel):
    date: str
    tokens: int
    cost_usd: Decimal
    reports: int


class UsageSeriesResponse(BaseModel):
    series: list[UsageSeriesPoint]
    total_tokens: int
    total_cost_usd: Decimal


class ModelBreakdownItem(BaseModel):
    model: str
    tokens: int
    cost_usd: Decimal
    pct: int


class ModelBreakdownResponse(BaseModel):
    breakdown: list[ModelBreakdownItem]


class DeviceBreakdownItem(BaseModel):
    device_type: str
    count: int


class OSBreakdownItem(BaseModel):
    os: str
    count: int


class BrowserBreakdownItem(BaseModel):
    browser: str
    count: int


class DeviceBreakdownResponse(BaseModel):
    devices: list[DeviceBreakdownItem]
    os: list[OSBreakdownItem]
    browsers: list[BrowserBreakdownItem]
