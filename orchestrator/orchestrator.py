"""
CLI entry point — run from project root:
    python -m orchestrator.orchestrator "your research question"
    python orchestrator/orchestrator.py "your research question"
"""
import asyncio
import sys

from .runner import run_orchestrator

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Universal Research Agent")
    parser.add_argument("problem", nargs="*", help="Research question")
    parser.add_argument(
        "--depth",
        choices=["shallow", "standard", "deep"],
        default="standard",
        help="Report depth: shallow (fast, 3-5 nodes), standard (default, 7-10 nodes), deep (thorough, 15-20 nodes)",
    )
    parser.add_argument("--audience", default="", help="Target audience (layperson/student/practitioner/expert/executive)")
    parser.add_argument("--lang", default="en", help="Output language code (default: en)")
    args = parser.parse_args()

    problem = " ".join(args.problem) if args.problem else (
        "What are the most effective patterns for designing multi-agent LLM systems "
        "as an AI Engineer? Focus on communication protocols, context passing, and reliable execution."
    )

    print(f"Executing: {problem}")
    print(f"Depth    : {args.depth}")

    async def main_run():
        ctx = await run_orchestrator(problem, audience=args.audience, output_language=args.lang, depth=args.depth)

        # ── Find the output document ──────────────────────────────────
        output_data = None
        for slot, data in ctx.results.items():
            if isinstance(data, dict) and "format" in data and "content" in data:
                output_data = data
                break

        # ── Build the Markdown report ─────────────────────────────────
        if output_data:
            content: str = output_data.get("content", "").strip()

            # Coverage gaps section
            gaps = output_data.get("coverage_gaps_disclosed", [])
            gaps_md = ""
            if gaps:
                gap_lines = "\n".join(f"- {g}" for g in gaps)
                gaps_md = f"\n\n---\n\n## Coverage Gaps\n\n{gap_lines}"

            # Bibliography from citation registry
            bib_md = ""
            if ctx.citation_registry:
                bib_text = ctx.citation_registry.format_bibliography()
                if bib_text.strip():
                    bib_md = f"\n\n---\n\n## References\n\n{bib_text}"

            # Credibility footer
            cred_md = ""
            if ctx.credibility_scores:
                avg = sum(ctx.credibility_scores.values()) / len(ctx.credibility_scores)
                cred_md = f"\n\n---\n\n*Mean source credibility: {avg:.2f} / 1.00*"

            report_content = (
                f"# Research Report\n\n"
                f"**Query:** {problem}\n\n"
                f"---\n\n"
                f"{content}"
                f"{gaps_md}"
                f"{bib_md}"
                f"{cred_md}\n"
            )
        else:
            report_content = (
                "# Research Report\n\n"
                f"**Query:** {problem}\n\n"
                "> No output document was generated — the pipeline may have failed. "
                "See console output for details.\n"
            )

        with open("final_report.md", "w", encoding="utf-8") as f:
            f.write(report_content)

        print("Saved to final_report.md")

    asyncio.run(main_run())
