# Research Run — live progress streaming + UI

Implement the "Research Run" live view (design: `next-frontend-context-review/project/Research Run.dc.html`)
against the **real** research workflow, driving fixed design components with dynamic data.

## Decisions (locked)
- **View placement:** new `frontend/src/components/views/research-run-view.tsx` (mirrors chat/report views).
- **Sandbox/console cards:** omit until real events exist. Sandboxes telemetry = 0.
- **Backend scope:** add `scope`, `agent_dispatch`, `source_added`, `section_written` events (data already exists at each site).

## Event contract (normalized `research.progress` payload)
All progress events keep the existing SSE event name `research.progress` (DB/replay/tests unchanged).
The payload gains a stable **`kind`** discriminator → one design component each:

| kind | source site | payload fields | design component |
|------|-------------|----------------|------------------|
| `phase` | `langgraph_runtime` phase nodes (existing) | `phase`, `status`, `message`, optional `cycle`,`node_count` | Pipeline row + phase divider + thought |
| `scope` | after `polish_prompt` | `objective`, `must_haves[]`, `deliverable` (from polished_objective) | Note/scope card |
| `agent_dispatch` | after `plan_lead` merge, per DAG node | `node_id`, `question` | Agent dispatch chip |
| `tool_call` | resolver `tool_dispatched`/`tool_completed`/`tool_failed` (existing) | `tool_name`, `node_id`, `status`, `source_count`, `elapsed_seconds` | Tool chip / web_search card |
| `source_added` | resolver node result, per new source_record | `title`, `url`, `source_type`, `node_id` | "Source added" line + Sources counter |
| `section_written` | after `write_report`, per section | `section_title` | "Wrote section" line |

Notes:
- Existing resolver statuses (`node_started`, `tool_reformulating`, `source_unavailable`, `node_completed`) are retained
  and carry `kind:"tool_call"` or `kind:"phase"` as appropriate; frontend can ignore unknown statuses safely.
- **Telemetry** (Sources / Tool calls / Sandboxes / Tokens) is **derived on the frontend** by reducing the event stream —
  no backend counters. Sandboxes = 0 (no container/sandbox events in the real workflow). Tokens = heuristic (feed length),
  clearly a display estimate.
- Terminal events unchanged: `research.completed` / `research.failed` / `research.cancelled` drive the report-ready card.
- Backward compatible: adding `kind` to payloads and adding new statuses does not break the existing thin reducer.

## Dependency graph
```
Task 1 (event contract: emit kind + new events)  ──┐
                                                    ├─► Task 3 (frontend event types + reducer)
Task 2 (SSE/schema: no change needed, verify)  ─────┘         │
                                                              ├─► Task 4 (design components: pipeline, telemetry, feed items)
                                                              │
                                                              └─► Task 5 (research-run-view assembly + wiring into view switch)
                                                                          │
                                                                          └─► Task 6 (verify end-to-end w/ test-mode run)
```
Vertical slices: each task delivers one complete path (backend emit → payload shape → frontend consume → render).

## Checkpoints
- **CP-A** after Task 1–2: backend emits the full contract; unit tests green; a test-mode run's JSONL diagnostics show every kind.
- **CP-B** after Task 4: components render from static fixture data (Storybook-free: a `__fixtures` array), light+dark.
- **CP-C** after Task 6: a real test-mode run streams into the live view end-to-end.

## Out of scope
- Container/sandbox execution events (no backend). Token accounting from provider usage (heuristic only for now).
- Report rendering changes (final report already handled by report-view; run-view links to it).
