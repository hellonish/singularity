"""
CLI entry point — run from project root:
    python -m orchestrator.orchestrator "your research question"
    python orchestrator/orchestrator.py "your research question"
"""
import asyncio
import sys

from .runner import run_orchestrator

if __name__ == "__main__":
    problem  = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else (
        "What are the GDPR implications of using a third-party LLM API "
        "to process EU customer data in a SaaS product?"
    )
    asyncio.run(run_orchestrator(problem))
