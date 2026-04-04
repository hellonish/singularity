"""
Quick local smoke-test for the research pipeline at strength=1.
Run from repo root:
    python test_pipeline_local.py
"""
import asyncio
import logging
import os
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    stream=sys.stdout,
)

# Load .env so QDRANT_*, TAVILY_*, etc. are available
from dotenv import load_dotenv
load_dotenv()

# Force in-memory Qdrant to avoid needing Qdrant Cloud locally
os.environ.setdefault("QDRANT_FORCE_IN_MEMORY", "1")

from agents.orchestrator.pipeline import run_pipeline


async def main() -> None:
    query = "What is dark matter?"
    model_id = "grok-3-mini-fast"
    llm_api_key = os.environ["GROK_API_KEY"]

    print(f"\n{'='*60}")
    print(f"Query   : {query}")
    print(f"Model   : {model_id}")
    print(f"Strength: 1 (minimal)")
    print(f"{'='*60}\n")

    async def on_phase(phase: str, description: str) -> None:
        print(f"\n[PHASE] {phase}: {description}")

    async def on_activity(activity: dict) -> None:
        kind = activity.get("kind", "")
        meta = activity.get("meta", {})
        print(f"  [ACT] {kind} {meta}")

    markdown = await run_pipeline(
        query=query,
        strength=1,
        on_phase=on_phase,
        on_activity=on_activity,
        model_id=model_id,
        llm_api_key=llm_api_key,
    )

    print(f"\n{'='*60}")
    print("REPORT (first 2000 chars):")
    print(f"{'='*60}")
    print(markdown[:2000])
    print(f"\n[Total length: {len(markdown)} chars]")


if __name__ == "__main__":
    asyncio.run(main())
