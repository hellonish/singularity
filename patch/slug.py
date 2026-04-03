"""
Slug matching — fuzzy text selection matching for patch operations.

When a user selects text in the frontend and the exact text doesn't match
the server's copy (e.g., due to whitespace differences), this module
attempts fuzzy matching to find the correct location.
"""
from __future__ import annotations

import difflib
from typing import Optional


def fuzzy_match(
    selected_text: str,
    full_content: str,
    threshold: float = 0.85,
) -> Optional[str]:
    """
    Attempt to find a fuzzy match for the selected text within the full content.

    Uses a sliding window approach with SequenceMatcher for similarity scoring.

    Args:
        selected_text: The text the user selected.
        full_content: The full document to search within.
        threshold: Minimum similarity ratio (0.0-1.0) for a match.

    Returns:
        The best matching substring from full_content, or None if no match
        exceeds the threshold.
    """
    if not selected_text or not full_content:
        return None

    selected_len = len(selected_text)
    content_len = len(full_content)

    if selected_len > content_len:
        return None

    # Normalize whitespace for matching
    norm_selected = _normalize_ws(selected_text)

    best_ratio = 0.0
    best_match: Optional[str] = None

    # Sliding window: try different window sizes around the original length
    for window_delta in range(0, min(selected_len // 2, 200), 10):
        window_size = selected_len + window_delta
        if window_size > content_len:
            break

        step = max(window_size // 4, 50)
        for offset in range(0, content_len - window_size + 1, step):
            candidate = full_content[offset:offset + window_size]
            ratio = difflib.SequenceMatcher(
                None, norm_selected, _normalize_ws(candidate)
            ).quick_ratio()

            if ratio > best_ratio:
                best_ratio = ratio
                best_match = candidate

            if best_ratio >= 0.95:
                break  # Good enough, stop early

        if best_ratio >= 0.95:
            break

    if best_ratio >= threshold and best_match is not None:
        return best_match

    return None


def find_heading_slug(content: str, heading: str) -> Optional[str]:
    """
    Find the content under a specific heading in markdown.

    Args:
        content: Full markdown document.
        heading: The heading text to find (without # prefix).

    Returns:
        The content of that section (from heading to next same-level heading or EOF),
        or None if heading not found.
    """
    lines = content.split("\n")
    heading_pattern = f"# {heading}"
    start_idx = None
    heading_level = None

    for i, line in enumerate(lines):
        if line.strip().lstrip("#").strip() == heading:
            start_idx = i
            heading_level = len(line) - len(line.lstrip("#"))
            break

    if start_idx is None:
        return None

    # Find end of section (next heading of same or higher level)
    end_idx = len(lines)
    for i in range(start_idx + 1, len(lines)):
        line = lines[i]
        if line.startswith("#"):
            level = len(line) - len(line.lstrip("#"))
            if level <= heading_level:
                end_idx = i
                break

    return "\n".join(lines[start_idx:end_idx])


def _normalize_ws(text: str) -> str:
    """Normalize whitespace for comparison."""
    import re
    return re.sub(r'\s+', ' ', text).strip()
