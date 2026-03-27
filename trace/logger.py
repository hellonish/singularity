"""
TraceLogger — structured execution trace for the research pipeline.

Writes a human-browsable folder of Markdown files + a machine-readable
`trace.jsonl` so every LLM prompt, response, skill call, and intermediate
output can be inspected after a run.

Output layout
─────────────
traces/
  <run_id>/
    00_overview.md            run metadata (query, strength, models used)
    01_phase_b/
      manager_1.md            system prompt + user message + raw LLM response
      manager_2.md
      manager_3.md
      lead.md                 proposals JSON sent + raw response + final tree
    02_phase_a/
      retriever_plan.md       LLM prompt + response + parsed skill_queries
      skills/
        web_search.md         per-skill queries + result summary
        academic_search.md
        ...
    03_phase_c/
      <node_id>_<title>/
        call1_analysis.md     analysis prompt + raw response + parsed JSON
        call2_write.md        write prompt + raw response + parsed JSON
    04_phase_d/
      polish.md               polisher input + output per section
    trace.jsonl               all events in chronological order (JSON Lines)

Usage
─────
    logger = TraceLogger(run_id="abc123", query="…", trace_root="traces")
    # pass `logger` to pipeline functions; pass None to disable all tracing
"""
from __future__ import annotations

import json
import re
import textwrap
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class TraceLogger:
    """
    Records every LLM call and skill invocation to a structured trace directory.

    All public methods are no-ops when `enabled=False`, so callers can always
    pass the logger reference without guarding every call site.
    """

    def __init__(
        self,
        run_id: str,
        query: str,
        trace_root: str | Path = "traces",
        enabled: bool = True,
    ) -> None:
        self.run_id  = run_id
        self.query   = query
        self.enabled = enabled
        self._seq    = 0          # global event sequence counter
        self._start  = datetime.now(timezone.utc)

        if not enabled:
            return

        self._root = Path(trace_root) / run_id
        self._jsonl_path = self._root / "trace.jsonl"
        self._root.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Overview
    # ------------------------------------------------------------------

    def write_overview(self, metadata: dict[str, Any]) -> None:
        """Write the top-level run summary (call once at pipeline start)."""
        if not self.enabled:
            return
        lines = [
            "# Run Overview",
            "",
            f"**Run ID** : `{self.run_id}`",
            f"**Query**  : {self.query}",
            f"**Started**: {self._start.strftime('%Y-%m-%d %H:%M:%S UTC')}",
            "",
            "## Configuration",
            "",
        ]
        for k, v in metadata.items():
            lines.append(f"- **{k}**: {v}")
        self._write_file("00_overview.md", "\n".join(lines))
        self._append_event("overview", metadata)

    # ------------------------------------------------------------------
    # Phase B — Planning (Managers + Lead)
    # ------------------------------------------------------------------

    def log_manager(
        self,
        manager_id: int,
        system_prompt: str,
        user_message: str,
        raw_response: str,
        parsed_tree_dict: dict,
    ) -> None:
        """Log one Manager agent call (proposal)."""
        if not self.enabled:
            return
        path = f"01_phase_b/manager_{manager_id}.md"
        content = _section("System Prompt", system_prompt)
        content += _section("User Message", user_message)
        content += _section("Raw LLM Response", raw_response, code=True)
        content += _section("Parsed Tree (JSON)", json.dumps(parsed_tree_dict, indent=2), code=True, lang="json")
        self._write_file(path, f"# Manager {manager_id} — Report Structure Proposal\n\n" + content)
        self._append_event("manager_propose", {
            "manager_id": manager_id,
            "user_message": user_message,
            "raw_response": raw_response,
            "node_count": len(parsed_tree_dict.get("nodes", [])),
        })

    def log_lead(
        self,
        system_prompt: str,
        user_message: str,
        raw_response: str,
        final_tree_dict: dict,
    ) -> None:
        """Log the Lead agent finalisation call."""
        if not self.enabled:
            return
        path = "01_phase_b/lead.md"
        content = _section("System Prompt", system_prompt)
        content += _section("User Message (includes Manager Proposals)", user_message)
        content += _section("Raw LLM Response", raw_response, code=True)
        content += _section("Final Tree (JSON)", json.dumps(final_tree_dict, indent=2), code=True, lang="json")
        self._write_file(path, "# Lead Agent — Final Report Structure\n\n" + content)
        self._append_event("lead_finalise", {
            "user_message": user_message,
            "raw_response": raw_response,
            "node_count": len(final_tree_dict.get("nodes", [])),
        })

    # ------------------------------------------------------------------
    # Phase A — Retrieval
    # ------------------------------------------------------------------

    def log_retriever_plan(
        self,
        system_prompt: str,
        user_prompt: str,
        raw_response: str,
        skill_queries: dict[str, list[str]],
    ) -> None:
        """Log the LLM skill-selection plan from the Retriever."""
        if not self.enabled:
            return
        path = "02_phase_a/retriever_plan.md"
        content  = _section("System Prompt", system_prompt)
        content += _section("User Prompt", user_prompt)
        content += _section("Raw LLM Response", raw_response, code=True)
        content += _section(
            "Parsed Skill Queries (JSON)",
            json.dumps(skill_queries, indent=2),
            code=True, lang="json",
        )
        self._write_file(path, "# Retriever — Skill Selection Plan\n\n" + content)
        self._append_event("retriever_plan", {
            "user_prompt": user_prompt,
            "raw_response": raw_response,
            "skill_queries": skill_queries,
        })

    def log_skill_result(
        self,
        skill_name: str,
        queries: list[str],
        sources_found: int,
        chunks_stored: int,
    ) -> None:
        """Log summary of one retrieval skill fanout."""
        if not self.enabled:
            return
        path = f"02_phase_a/skills/{skill_name}.md"
        lines = [
            f"# Skill: `{skill_name}`",
            "",
            f"**Sources found** : {sources_found}",
            f"**Chunks stored** : {chunks_stored}",
            "",
            "## Queries",
            "",
        ]
        for i, q in enumerate(queries, 1):
            lines.append(f"{i}. {q}")
        self._write_file(path, "\n".join(lines))
        self._append_event("skill_result", {
            "skill": skill_name,
            "queries": queries,
            "sources_found": sources_found,
            "chunks_stored": chunks_stored,
        })

    # ------------------------------------------------------------------
    # Phase C — Writing (Worker agents)
    # ------------------------------------------------------------------

    def log_worker_call1(
        self,
        node_id: str,
        node_title: str,
        system_prompt: str,
        user_message: str,
        raw_response: str,
        parsed: dict,
    ) -> None:
        """Log Worker Call 1 (multi-analysis)."""
        if not self.enabled:
            return
        path = f"03_phase_c/{_slug(node_id, node_title)}/call1_analysis.md"
        content  = _section("System Prompt", system_prompt)
        content += _section("User Message (chunks + children content)", user_message)
        content += _section("Raw LLM Response", raw_response, code=True)
        content += _section("Parsed JSON", json.dumps(parsed, indent=2), code=True, lang="json")
        header = f"# `{node_id}` — {node_title}\n## Call 1 · Analysis\n\n"
        self._write_file(path, header + content)
        self._append_event("worker_call1", {
            "node_id": node_id,
            "node_title": node_title,
            "user_message": user_message,
            "raw_response": raw_response,
            "parsed": parsed,
        })

    def log_worker_call2(
        self,
        node_id: str,
        node_title: str,
        system_prompt: str,
        user_message: str,
        raw_response: str,
        parsed: dict,
        final_content: str,
    ) -> None:
        """Log Worker Call 2 (section write)."""
        if not self.enabled:
            return
        path = f"03_phase_c/{_slug(node_id, node_title)}/call2_write.md"
        content  = _section("System Prompt", system_prompt)
        content += _section("User Message (analysis + evidence)", user_message)
        content += _section("Raw LLM Response", raw_response, code=True)
        content += _section("Parsed JSON", json.dumps(parsed, indent=2), code=True, lang="json")
        content += _section("Final Section Content (written prose)", final_content)
        header = f"# `{node_id}` — {node_title}\n## Call 2 · Write\n\n"
        self._write_file(path, header + content)
        self._append_event("worker_call2", {
            "node_id": node_id,
            "node_title": node_title,
            "user_message": user_message,
            "raw_response": raw_response,
            "final_content": final_content,
            "word_count": len(final_content.split()),
        })

    # ------------------------------------------------------------------
    # Phase D — Polish
    # ------------------------------------------------------------------

    def log_polish(
        self,
        system_prompt: str,
        user_message: str,
        raw_response: str,
        section_idx: int = 0,
    ) -> None:
        """Log one polisher LLM call."""
        if not self.enabled:
            return
        path = f"04_phase_d/polish_section_{section_idx:03d}.md"
        content  = _section("System Prompt", system_prompt)
        content += _section("User Message", user_message)
        content += _section("Raw LLM Response", raw_response, code=True)
        self._write_file(path, f"# Phase D — Polish  (section {section_idx})\n\n" + content)
        self._append_event("polish", {
            "section_idx": section_idx,
            "user_message": user_message,
            "raw_response": raw_response,
        })

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _write_file(self, relative_path: str, content: str) -> None:
        target = self._root / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    def _append_event(self, event_type: str, payload: dict) -> None:
        self._seq += 1
        event = {
            "seq":       self._seq,
            "ts":        datetime.now(timezone.utc).isoformat(),
            "event":     event_type,
            "run_id":    self.run_id,
            **payload,
        }
        with self._jsonl_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event, ensure_ascii=False, default=str) + "\n")


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def _section(title: str, body: str, code: bool = False, lang: str = "") -> str:
    """Render one headed section in a Markdown document."""
    fence = f"```{lang}" if lang else "```"
    if code:
        block = f"{fence}\n{body}\n```\n"
    else:
        # Indent prose so it doesn't clash with surrounding headings
        block = textwrap.indent(body, "") + "\n"
    return f"## {title}\n\n{block}\n"


def _slug(node_id: str, title: str) -> str:
    """Derive a filesystem-safe directory name from a node id + title."""
    safe_title = re.sub(r"[^\w\s-]", "", title).strip().replace(" ", "_")[:40]
    return f"{node_id}_{safe_title}"
