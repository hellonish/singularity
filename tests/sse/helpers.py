from __future__ import annotations

import json
from typing import Any


def parse_sse(payload: str) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for block in payload.strip().split("\n\n"):
        fields: dict[str, str] = {}
        data_lines: list[str] = []
        for line in block.splitlines():
            if line.startswith("data: "):
                data_lines.append(line.removeprefix("data: "))
            elif ": " in line:
                key, value = line.split(": ", 1)
                fields[key] = value
        events.append(
            {
                "id": fields.get("id"),
                "event": fields["event"],
                "data": json.loads("\n".join(data_lines)),
            }
        )
    return events
