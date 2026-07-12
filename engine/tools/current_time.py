"""Current time and bounded date arithmetic using IANA time zones."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .base import ToolBase, ToolResult


class CurrentTimeTool(ToolBase):
    name = "current_time"
    description = "Return current or supplied ISO time in an IANA timezone with bounded date arithmetic."
    skill_ids = ("temporal_reasoning",)

    async def call(
        self,
        query: str,
        timezone_name: str = "UTC",
        at_iso: str | None = None,
        add_days: int = 0,
        add_hours: int = 0,
        **kwargs,
    ) -> ToolResult:
        try:
            zone = ZoneInfo(timezone_name)
        except ZoneInfoNotFoundError as exc:
            raise ValueError(f"Unknown IANA timezone: {timezone_name}") from exc
        if at_iso:
            value = datetime.fromisoformat(at_iso.replace("Z", "+00:00"))
            if value.tzinfo is None:
                value = value.replace(tzinfo=timezone.utc)
        else:
            value = datetime.now(timezone.utc)
        value = value.astimezone(zone) + timedelta(days=add_days, hours=add_hours)
        content = value.isoformat()
        return ToolResult(
            content=content,
            sources=[],
            credibility_base=1.0,
            raw={"timezone": timezone_name, "iso": content, "utc_offset": value.strftime("%z")},
        )
