"""
CLI entry point — run from project root:

    # Legacy DAG mode (--depth):
    python -m agents.orchestrator.cli "your question" --depth shallow

    # Phase 5 product mode (--strength):
    python -m agents.orchestrator.cli "your question" --strength 5
    python -m agents.orchestrator.cli "your question" --strength 10 --audience expert
"""
import asyncio
from datetime import datetime
from pathlib import Path

from .runner import run_orchestrator
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
    print("Saved  →  final_report.html")


def _legacy_run(problem: str, depth: str, audience: str, lang: str) -> None:
    """Original DAG-based pipeline (--depth flag)."""

    async def main_run():
        ctx = await run_orchestrator(
            problem, audience=audience, output_language=lang, depth=depth
        )

        output_data = None
        if ctx.final_output_slot and ctx.final_output_slot in ctx.results:
            output_data = ctx.results[ctx.final_output_slot]
        else:
            _PRIMARY = {
                "report_generator", "exec_summary", "explainer",
                "decision_matrix", "knowledge_delta",
            }
            for slot, data in ctx.results.items():
                if isinstance(data, dict) and data.get("skill_name") in _PRIMARY:
                    output_data = data

        if output_data:
            content = output_data.get("content", "").strip()
            gaps = output_data.get("coverage_gaps_disclosed", [])
            gaps_md = (
                "\n\n---\n\n## Coverage Gaps\n\n" + "\n".join(f"- {g}" for g in gaps)
                if gaps else ""
            )
            bib_md = ""
            if ctx.citation_registry:
                bib_text = ctx.citation_registry.format_bibliography()
                if bib_text.strip():
                    bib_md = f"\n\n---\n\n## References\n\n{bib_text}"
            cred_md = ""
            if ctx.credibility_scores:
                avg = sum(ctx.credibility_scores.values()) / len(ctx.credibility_scores)
                cred_md = f"\n\n---\n\n*Mean source credibility: {avg:.2f} / 1.00*"
            report_md = (
                f"# Research Report\n\n**Query:** {problem}\n\n---\n\n"
                f"{content}{gaps_md}{bib_md}{cred_md}\n"
            )
        else:
            report_md = (
                f"# Research Report\n\n**Query:** {problem}\n\n"
                "> No output document was generated — the pipeline may have failed.\n"
            )

        _save_report(
            report_md,
            query=problem,
            metadata={
                "audience": audience or "practitioner",
                "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            },
        )

    asyncio.run(main_run())


def _strength_run(
    problem: str,
    strength: int,
    audience: str,
    lang: str,
    trace: bool = False,
) -> None:
    """Phase 5 strength-based product pipeline."""

    async def main_run():
        report_md = await run_pipeline(
            query=problem,
            strength=strength,
            audience=audience or "practitioner",
            output_language=lang,
            trace=trace,
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
            "  python -m agents.orchestrator.cli \"AI safety\" --strength 5\n"
            "  python -m agents.orchestrator.cli \"AI safety\" --depth shallow\n"
        ),
    )
    parser.add_argument("problem", nargs="*", help="Research question")

    # ── Mode: strength (Phase 5) OR depth (legacy) ───────────────────
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--strength",
        type=int,
        choices=range(1, 11),
        metavar="1-10",
        help="[Phase 5] Report strength 1–10. Controls breadth and depth.",
    )
    mode.add_argument(
        "--depth",
        choices=["shallow", "standard", "deep"],
        default=None,
        help="[Legacy] shallow / standard / deep DAG run.",
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
    args = parser.parse_args()

    problem = " ".join(args.problem) if args.problem else (
        "What are the most effective patterns for designing multi-agent LLM systems "
        "as an AI Engineer?"
    )

    if args.strength is not None:
        print(f"Executing : {problem}")
        print(f"Strength  : {args.strength}")
        _strength_run(problem, args.strength, args.audience, args.lang, trace=args.trace)
    else:
        depth = args.depth or "standard"
        print(f"Executing: {problem}")
        print(f"Depth    : {depth}")
        _legacy_run(problem, depth, args.audience, args.lang)
