"""
Patch service — applies LLM-driven edits to report sections.

Given a report version, a selected text range, and an instruction,
this module:
1. Validates the selection and instruction
2. Calls the LLM to produce a patched section
3. Returns the new full content for version creation
"""
from __future__ import annotations

import re
from typing import Optional

from llm.router import get_llm_client


async def apply_patch(
    full_content: str,
    selected_text: str,
    instruction: str,
    *,
    api_key: str,
    model_id: str = "grok-3-mini",
) -> str:
    """
    Apply a natural-language edit instruction to a section of the report.

    Args:
        full_content: The complete markdown report content.
        selected_text: The exact text the user selected for editing.
        instruction: The user's edit instruction (e.g., "Make this more concise").
        api_key: User's provider API key (BYOK).
        model_id: Which LLM to use for the patch.

    Returns:
        The full content with the selected section replaced by the LLM output.

    Raises:
        PatchError: If the patch cannot be applied.
    """
    # Validate the selection exists in content
    if selected_text not in full_content:
        from patch.slug import fuzzy_match
        match_result = fuzzy_match(selected_text, full_content)
        if match_result:
            selected_text = match_result
        else:
            raise PatchError("Selected text not found in report content")

    # Build the patch prompt
    system_prompt = (
        "You are an expert editor. You are given a section of a research report "
        "and an instruction to modify it. Apply the instruction precisely.\n\n"
        "Rules:\n"
        "- Output ONLY the replacement text for the selected section.\n"
        "- Do NOT wrap the output in markdown code blocks.\n"
        "- Do NOT add explanations or commentary.\n"
        "- Maintain the same heading level and formatting style.\n"
        "- Preserve all markdown formatting (links, bold, italic, lists, tables).\n"
        "- If the instruction asks to expand, do not exceed 3x the original length.\n"
        "- If the instruction asks to reduce, keep the core information.\n"
    )

    user_prompt = (
        f"--- SELECTED TEXT ---\n{selected_text}\n--- END SELECTED TEXT ---\n\n"
        f"--- INSTRUCTION ---\n{instruction}\n--- END INSTRUCTION ---"
    )

    # Call the LLM
    client = get_llm_client(model_id, api_key)
    response = await client.chat(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.3,
        max_tokens=len(selected_text) * 4,  # Allow up to 4x expansion
    )

    replacement = response.strip()

    # Validate the replacement isn't empty
    if not replacement:
        raise PatchError("LLM returned empty response for patch")

    # Validate size constraint (max 3x original)
    from patch.validator import validate_patch_size
    validate_patch_size(selected_text, replacement)

    # Validate no unsafe content
    from patch.validator import validate_safety
    validate_safety(replacement)

    # Replace in the full content
    new_content = full_content.replace(selected_text, replacement, 1)

    return new_content


class PatchError(Exception):
    """Raised when a patch operation fails."""
    pass
