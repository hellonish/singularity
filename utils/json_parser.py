"""
Shared JSON extraction utilities for parsing LLM responses.

LLM output often wraps JSON in markdown fences, includes prose before the
object, or contains unescaped newlines inside string values. This module
provides a single set of strategies used by all agents instead of each
maintaining its own duplicate implementation.

Public API
----------
extract_object(text)          -> dict | None
    Try fenced block → raw parse → iterate from first '{'.

sanitize_string_values(text)  -> str
    Escape literal newlines/carriage-returns inside JSON string values.

extract_string_field(text, key) -> str | None
    Pull a single string field from JSON text using raw_decode so escaped
    inner quotes are handled correctly.
"""
from __future__ import annotations

import json
import re


def extract_object(text: str) -> dict | None:
    """
    Extract the first JSON object from `text`.

    Strategy 1 — fenced block: looks for ```json ... ``` or ``` ... ```.
    Strategy 2 — raw parse: tries json.loads on the full stripped text.
    Strategy 3 — iterate: scans every '{' and attempts raw_decode from there.

    Returns the parsed dict, or None if all strategies fail.
    """
    decoder = json.JSONDecoder()

    def _try(candidate: str) -> dict | None:
        candidate = candidate.strip()
        if not candidate:
            return None
        for loader in (
            lambda t: json.loads(t),
            lambda t: decoder.raw_decode(t)[0],
        ):
            try:
                result = loader(candidate)
                if isinstance(result, dict):
                    return result
            except (json.JSONDecodeError, ValueError):
                continue
        return None

    # Strategy 1: markdown fenced block
    for block in re.findall(r"```(?:json)?\s*\n(.*?)\n```", text, re.DOTALL):
        result = _try(block)
        if result is not None:
            return result

    # Strategy 2: whole text
    result = _try(text.strip())
    if result is not None:
        return result

    # Strategy 3: scan from each '{'
    for match in re.finditer(r"\{", text):
        try:
            candidate, _ = decoder.raw_decode(text, match.start())
            if isinstance(candidate, dict):
                return candidate
        except (json.JSONDecodeError, ValueError):
            continue

    return None


def sanitize_string_values(text: str) -> str:
    """
    Escape literal newline and carriage-return characters that appear inside
    JSON string values, converting them to the valid escape sequences \\n
    and \\r.

    LLMs sometimes emit multi-line JSON strings with real newlines instead of
    \\n, which makes json.loads fail. This scanner fixes that without touching
    structural whitespace between keys and values.
    """
    result: list[str] = []
    in_string = False
    escape_next = False
    for ch in text:
        if escape_next:
            result.append(ch)
            escape_next = False
        elif ch == "\\":
            result.append(ch)
            escape_next = True
        elif ch == '"':
            result.append(ch)
            in_string = not in_string
        elif in_string and ch == "\n":
            result.append("\\n")
        elif in_string and ch == "\r":
            result.append("\\r")
        else:
            result.append(ch)
    return "".join(result)


def extract_string_field(text: str, key: str) -> str | None:
    """
    Locate `"key": "<json string value>"` inside `text` and decode the string
    using json.JSONDecoder.raw_decode, which correctly handles escaped quotes,
    backslashes, newlines, and unicode escape sequences.

    Returns the decoded string value, or None if the field is not found.
    """
    match = re.search(r'"%s"\s*:\s*"' % re.escape(key), text)
    if not match:
        return None
    pos = match.end() - 1   # index of the opening '"' of the value
    try:
        value, _ = json.JSONDecoder().raw_decode(text[pos:])
        return value if isinstance(value, str) else None
    except (json.JSONDecodeError, ValueError):
        return None
