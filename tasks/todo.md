# Research Run — todo

## Task 1 — Backend: emit normalized event contract
- [ ] Add `kind` to phase events in `engine/research_workflow/langgraph_runtime.py` `progress()`
- [ ] Emit `scope` after `polish_prompt` from `polished_objective` (objective/must_haves/deliverable)
- [ ] Emit `agent_dispatch` per DAG node after `plan_lead`
- [ ] Emit `section_written` per section after `write_report`
- [ ] Add `kind:"tool_call"` to resolver events in `engine/research_workflow/resolver.py`
- [ ] Emit `source_added` per new source_record in `api/research_runtime.py` resolver wrapper (data already there)
- **AC:** a test-mode run's `latest-research-diagnostics.jsonl` contains ≥1 of each kind; existing progress fields intact.
- **Verify:** `pytest tests/engine -k "research or resolver or langgraph"`; inspect JSONL from `engine.cli` demo run.

## Task 2 — Backend: SSE/schema pass-through (verify only)
- [ ] Confirm `research.progress` payload passes `kind` through `append_event` → SSE untouched (JSON blob).
- **AC:** no schema change required; `ResearchRunEventRead.payload` already `dict[str,Any]`.
- **Verify:** `pytest tests/sse -k research`.

## Task 3 — Frontend: event types + reducer
- [ ] Add `ResearchEvent` discriminated union + `RunFeed`/`RunTelemetry`/`PipelinePhase` types to `frontend/src/lib/api.ts`
- [ ] Extend `streamResearch` in `workspace-provider.tsx` to accumulate a per-run **feed** + derived telemetry + pipeline state (keep existing thin `runActivity` for report-view).
- **AC:** reducer maps each `kind` to a feed item; telemetry counters increment; pipeline phase transitions queued→live→done.
- **Verify:** unit test the reducer with a fixture event array (frontend test or a small node script).

## Task 4 — Frontend: fixed design components (data-pluggable)
- [ ] `PipelineRail` (6 phases, queued/live/done)
- [ ] `LiveTelemetry` (Sources/Tool calls/Sandboxes/Tokens tiles)
- [ ] `RunFeed` item renderers: phase divider, thought, agent chip, source line, scope card, tool chip, web_search card, section-written line, running dots
- [ ] Top chrome (elapsed, depth, model chips, stop/replay) + query bar + report-ready card
- [ ] Drive from a `__fixtures` prop for CP-B
- **AC:** renders in light+dark from static fixture; matches design tokens (Newsreader/JetBrains Mono, `--surface`/`--accent-2`).
- **Verify:** preview_start dev server, screenshot fixture render both themes.

## Task 5 — Frontend: assemble research-run-view + wire in
- [ ] `research-run-view.tsx` composes rail + feed + chrome from live workspace state
- [ ] Wire into view switching (app-store/dashboard) so an active run opens this view; Stop = cancelResearch; on completion link to report
- **AC:** starting a run navigates to the live view; cancel works; completion shows report-ready card → open report.
- **Verify:** click-through in preview against a running test-mode run.

## Task 6 — End-to-end verification
- [ ] Run a real test-mode research run; confirm every component populates from live SSE.
- **AC:** feed shows scope→agents→searches→sources→sections→report; telemetry non-zero; no console errors.
- **Verify:** preview browser, read_console_messages, screenshot final state.

## Checkpoints
- [x] CP-A (after 1–2): backend contract complete, tests green (115 backend tests pass)
- [x] CP-B (after 4): components render from fixtures, both themes (verified in browser, no console errors)
- [~] CP-C (after 6): live run end-to-end — deferred by user. Verified instead via: reducer replay of 85 real
      historical (pre-`kind`) events (backward-compatible, no crash), fixture render both themes, prod build passes.
      A real budget-spending run to be triggered by the user later.
