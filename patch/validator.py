"""
Patch validation — safety and size checks for LLM-generated patches.
"""
from __future__ import annotations

import re
from typing import Optional

from patch.service import PatchError


# Maximum expansion factor for patched content vs original
MAX_EXPANSION_FACTOR = 3.0

# Patterns that indicate unsafe content
_UNSAFE_PATTERNS = [
    re.compile(r'<script[^>]*>', re.IGNORECASE),
    re.compile(r'<iframe[^>]*>', re.IGNORECASE),
    re.compile(r'<object[^>]*>', re.IGNORECASE),
    re.compile(r'<embed[^>]*>', re.IGNORECASE),
    re.compile(r'javascript:', re.IGNORECASE),
    re.compile(r'on\w+\s*=', re.IGNORECASE),  # Event handlers like onclick=
    re.compile(r'<link[^>]*>', re.IGNORECASE),
    re.compile(r'<meta[^>]*>', re.IGNORECASE),
]

# Markdown AST node types considered unsafe
_UNSAFE_MD_NODES = {"html_block", "html_inline"}


def validate_patch_size(original: str, replacement: str) -> None:
    """
    Validate that the replacement text is not excessively larger than the original.

    Raises PatchError if replacement > 3x original length.
    """
    if len(replacement) > len(original) * MAX_EXPANSION_FACTOR:
        raise PatchError(
            f"Patched content exceeds maximum size: "
            f"{len(replacement)} chars vs {len(original)} original "
            f"(max {MAX_EXPANSION_FACTOR}x expansion)"
        )


def validate_safety(text: str) -> None:
    """
    Validate that the text does not contain unsafe HTML/script injection.

    Checks for common XSS vectors and unsafe HTML elements.
    Raises PatchError if unsafe content is detected.
    """
    for pattern in _UNSAFE_PATTERNS:
        if pattern.search(text):
            raise PatchError(
                f"Unsafe content detected in patch output. "
                f"Pattern matched: {pattern.pattern}"
            )


def validate_markdown_ast(text: str) -> None:
    """
    Validate markdown content using a simple AST check.

    This is a lightweight check that looks for raw HTML blocks
    and other potentially dangerous markdown constructs.
    """
    lines = text.split("\n")
    in_code_block = False

    for line in lines:
        # Track code blocks — content inside is safe
        if line.strip().startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue

        # Check for raw HTML lines (start with < and not a markdown-safe tag)
        stripped = line.strip()
        if stripped.startswith("<") and not _is_safe_html_tag(stripped):
            raise PatchError(
                f"Raw HTML detected in markdown output: {stripped[:100]}"
            )


def _is_safe_html_tag(line: str) -> bool:
    """
    Check if an HTML line uses only markdown-safe tags.

    These are tags commonly used in markdown rendering:
    br, hr, img, details, summary, sup, sub, mark, kbd
    """
    safe_tags = {"br", "hr", "img", "details", "summary", "sup", "sub", "mark", "kbd"}
    tag_match = re.match(r'<(/?\w+)', line)
    if tag_match:
        tag = tag_match.group(1).lstrip("/").lower()
        return tag in safe_tags
    return True


def validate_patch_instruction(instruction: str) -> None:
    """
    Validate that a patch instruction is reasonable.

    Prevents prompt injection and overly complex instructions.
    """
    if len(instruction) > 2000:
        raise PatchError("Instruction too long (max 2000 characters)")

    # Check for potential prompt injection
    injection_patterns = [
        re.compile(r'ignore\s+(previous|all|above)\s+instructions', re.IGNORECASE),
        re.compile(r'you\s+are\s+now', re.IGNORECASE),
        re.compile(r'system\s*:', re.IGNORECASE),
        re.compile(r'forget\s+(everything|all)', re.IGNORECASE),
    ]
    for pattern in injection_patterns:
        if pattern.search(instruction):
            raise PatchError("Potentially unsafe instruction detected")
