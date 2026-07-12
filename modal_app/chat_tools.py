"""Deployed Modal Function for trusted, skill-scoped chat tools."""
from __future__ import annotations

import os
from pathlib import Path

import modal

from engine.tools import TOOL_REGISTRY
from engine.tools.contracts import ChatToolInvocation, validate_chat_tool_invocation

app = modal.App("singularity-chat-tools")
tool_provider_secret = modal.Secret.from_name(
    os.getenv("SINGULARITY_MODAL_TOOL_SECRET", "singularity-tool-providers"),
)
tool_image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install(
        "aiohttp", "pydantic", "PyYAML", "certifi", "ddgs", "tavily-python", "arxiv", "biopython",
        "PyGithub", "huggingface-hub", "youtube-transcript-api", "pdfplumber", "PyMuPDF",
        "beautifulsoup4", "trafilatura", "playwright",
    )
    .run_commands("playwright install --with-deps chromium")
    .add_local_python_source("engine")
    # add_local_python_source only ships *.py; skill discovery globs
    # engine/skills/*/config.yaml and reads instructions.md at runtime, so the
    # non-Python skill data files must be copied into the same import path.
    .add_local_dir(
        Path(__file__).resolve().parent.parent / "engine" / "skills",
        remote_path="/root/engine/skills",
    )
)


@app.function(image=tool_image, secrets=[tool_provider_secret], timeout=420)
async def execute_chat_tool(task: dict) -> dict:
    invocation = validate_chat_tool_invocation(ChatToolInvocation.model_validate(task))
    if TOOL_REGISTRY.descriptor(invocation.tool_name).execution_kind != "trusted_function":
        raise ValueError(f"{invocation.tool_name} is not allowed in the trusted Function executor")
    tool = TOOL_REGISTRY.create(invocation.tool_name)
    result = await tool.call_with_retry(
        invocation.query,
        timeout=float(invocation.timeout_seconds),
        **invocation.arguments,
    )
    return {
        "content": result.content,
        "sources": result.sources,
        "credibility_base": result.credibility_base,
        "error": result.error,
    }
