"""
CLI entry point — run from project root:

    python -m agents.orchestrator.cli "your question" --strength 2
    python -m agents.orchestrator.cli "your question" --strength 3 --audience expert
"""
import asyncio
import logging
from datetime import datetime
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

from agents.chat.models import DEFAULT_MODEL_ID

from .pipeline import run_pipeline
from render import ReportHtmlRenderer


def _save_report(report_md: str, query: str, metadata: dict) -> None:
    """
    Renders the Markdown report to a self-contained HTML file (final_report.html).
    ReportHtmlRenderer embeds the Markdown client-side so KaTeX + Marked.js
    handle math, formatting, and advanced symbols in the browser.
    """
    html = ReportHtmlRenderer().render(report_md, query=query, metadata=metadata)
    Path("final_report.html").write_text(html, encoding="utf-8")
    logger.info("Saved  →  final_report.html")


def _strength_run(
    problem: str,
    strength: int,
    audience: str,
    lang: str,
    trace: bool,
    model_id: str,
    llm_api_key: str,
) -> None:
    """Phase 5 strength-based product pipeline."""

    async def main_run():
        report_md = await run_pipeline(
            query=problem,
            strength=strength,
            audience=audience or "practitioner",
            output_language=lang,
            trace=trace,
            model_id=model_id,
            llm_api_key=llm_api_key,
        )
        _save_report(
            report_md,
            query=problem,
            metadata={
                "strength": strength,
                "audience": audience or "practitioner",
                "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            },
        )

    asyncio.run(main_run())


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Universal Research Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python -m agents.orchestrator.cli \"AI safety\" --strength 2 --api-key YOUR_KEY\n"
            "  python -m agents.orchestrator.cli \"AI safety\" --strength 3 --model-id grok-3-mini --api-key KEY\n"
        ),
    )
    parser.add_argument("problem", nargs="*", help="Research question")

    parser.add_argument(
        "--strength",
        type=int,
        choices=[1, 2, 3],
        metavar="1|2|3",
        default=2,
        help="Intensity: 1=low, 2=medium, 3=high (default: 2).",
    )
    parser.add_argument(
        "--audience",
        default="",
        help="layperson / student / practitioner / expert / executive",
    )
    parser.add_argument("--lang", default="en", help="Output language (default: en)")
    parser.add_argument(
        "--trace",
        action="store_true",
        default=False,
        help=(
            "Enable execution trace logging. Writes a structured trace directory "
            "under traces/<run_id>/ with every LLM prompt, raw response, skill "
            "selection plan, and parsed output for all pipeline phases."
        ),
    )
    parser.add_argument(
        "--api-key",
        required=True,
        help="Provider API key for the selected model (BYOK; not read from .env).",
    )
    parser.add_argument(
        "--model-id",
        default=DEFAULT_MODEL_ID,
        help=f"Registered chat model id (default: {DEFAULT_MODEL_ID}).",
    )
    args = parser.parse_args()

    problem = " ".join(args.problem) if args.problem else (
        "What are the most effective patterns for designing multi-agent LLM systems "
        "as an AI Engineer?"
    )

    logger.info("Executing : %s", problem)
    logger.info("Strength  : %d", args.strength)
    _strength_run(
        problem,
        args.strength,
        args.audience,
        args.lang,
        trace=args.trace,
        model_id=args.model_id,
        llm_api_key=args.api_key,
    )
