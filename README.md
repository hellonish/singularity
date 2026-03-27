# Singularity — Deep Dive Study Report
## A Universal Research Agent: Architecture, Challenges, and Agentic AI Patterns

> **Purpose:** This report is a complete technical reference for the Singularity project. It is written to serve as both a post-mortem of how the system was designed and debugged, and as a study guide for understanding modern agentic AI systems from first principles.
>
> **Last updated:** March 2026. Reflects the current four-phase pipeline (B → A → C → D), tiered model routing, Qdrant vector store, and Phase D Report Polisher. The project has two execution modes: Legacy DAG (`--depth`) and Phase 5 Strength-Based Pipeline (`--strength`).

---

## Table of Contents

1. [What Is This Project?](#1-what-is-this-project)
2. [What Is Agentic AI? — Foundational Concepts](#2-what-is-agentic-ai--foundational-concepts)
3. [System Architecture Overview](#3-system-architecture-overview)
4. [The Planner — LLM-Driven DAG Generation](#4-the-planner--llm-driven-dag-generation)
5. [The Orchestrator — Execution Engine](#5-the-orchestrator--execution-engine)
6. [Skills — The Three-Tier Task System](#6-skills--the-three-tier-task-system)
7. [Tools — The Data Source Layer](#7-tools--the-data-source-layer)
8. [Context Management — Feeding the Right Information](#8-context-management--feeding-the-right-information)
9. [Citation & Credibility System](#9-citation--credibility-system)
10. [LLM Integration Layer](#10-llm-integration-layer)
11. [Domain Registry — Making the Agent Domain-Aware](#11-domain-registry--making-the-agent-domain-aware)
12. [Contracts — Data Shape Guarantees](#12-contracts--data-shape-guarantees)
13. [Bugs We Hit and How We Fixed Them](#13-bugs-we-hit-and-how-we-fixed-them)
14. [End-to-End Data Flow Walkthrough](#14-end-to-end-data-flow-walkthrough)
15. [Key Agentic AI Patterns Used in This Project](#15-key-agentic-ai-patterns-used-in-this-project)
16. [What We Learned — Lessons for Agentic AI Design](#16-what-we-learned--lessons-for-agentic-ai-design)

---

## 1. What Is This Project?

Singularity is a **universal research agent** — a system that takes a plain-English research question and autonomously produces a comprehensive, cited, audience-calibrated report on it.

You run it in one of two modes:

```bash
# Legacy DAG mode (--depth)
python -m agents.orchestrator.cli "research about spurious correlations in ML" --depth deep

# Phase 5 strength-based product mode (--strength 1–10)
python -m agents.orchestrator.cli "research about spurious correlations in ML" --strength 7 --audience expert
```

It then:

- Figures out what domain the question belongs to (ML research, medicine, law, finance, etc.)
- Plans a directed acyclic graph (DAG) of research tasks
- Executes those tasks in parallel and sequentially — searching arXiv, GitHub, HuggingFace, PubMed, SEC filings, court records, YouTube transcripts, and more
- Analyses what it finds using LLMs (synthesis, contradiction detection, causal analysis, gap analysis, etc.)
- Generates a formatted report with inline citations, a bibliography, and a credibility score
- If tasks fail, it re-plans and tries again — up to 5 rounds for deep mode

The system has **36 modular skills**, **14 data source connectors**, **11 domain bundles**, **3 LLM backends** (Grok, Gemini, DeepSeek), a **Qdrant vector store** for evidence retrieval, and a citation tracking system that generates a Reference List mapping inline citation keys to source URLs.

### Why build this?

This project is an exploration of how to build production-grade agentic AI systems. It forces you to confront every core challenge in agentic AI:

- How do you get an LLM to plan structured, executable workflows?
- How do you handle failures gracefully without cascading the whole system?
- How do you prevent LLMs from receiving irrelevant context and degrading?
- How do you measure and track the trustworthiness of information?
- How do you make a system self-correcting without infinite loops?

---

## 2. What Is Agentic AI? — Foundational Concepts

Before diving into the code, it's worth grounding ourselves in what "agentic AI" actually means, because the word is overloaded.

### 2.1 The Spectrum from Chatbot to Agent

A **chatbot** takes input and produces output in a single forward pass. No planning. No memory beyond the conversation. No tools.

An **agent** is a system where an LLM has access to tools and takes multiple actions over time to accomplish a goal, observing the results of each action before deciding the next one.

The key properties of an agent are:

| Property | Description |
|---|---|
| **Tool use** | The agent can call external functions (search, code execution, APIs) |
| **Multi-step reasoning** | The agent takes multiple actions before arriving at an answer |
| **Observation** | The agent sees the results of its actions and adjusts |
| **Planning** | The agent decides what to do next based on a goal |
| **Memory** | The agent retains state across steps |

Singularity sits at the **orchestration agent** level — it doesn't just use tools, it plans a complete multi-stage workflow, executes it, detects gaps, and replans.

### 2.2 The ReAct Loop

The foundational pattern for agentic AI is **ReAct** (Reasoning + Acting), introduced in a 2022 paper. The loop is:

```
Thought → Action → Observation → Thought → Action → ...
```

In Singularity, this maps to:

```
Plan (LLM thinks about what tasks to do)
  → Execute node (run a tool or LLM skill)
    → Record result (observation)
      → Gap analysis (did it work?)
        → Replan if needed (new thought)
```

### 2.3 DAG-Based vs. Linear Agents

Many early agents are **linear** — they do one thing, look at the result, do the next thing. This is simple but slow: everything is sequential, and you can't parallelize.

A more sophisticated pattern is the **DAG agent** (Directed Acyclic Graph). The planner generates a graph of tasks with dependency relationships. Tasks with no unresolved dependencies can run **in parallel**. This is what Singularity uses.

```
n1 (academic_search) ─┐
n2 (code_search)      ─┼─→ n7 (claim_verification) ─→ n10 (meta_analysis) ─→ ...
n3 (dataset_search)   ─┘
```

### 2.4 The Core Tensions in Agentic AI

Building agents surfaces several fundamental tensions that don't exist in simple LLM applications:

1. **Cost vs. Quality** — More thorough research means more LLM calls, more API calls, more latency, more money.
2. **Autonomy vs. Reliability** — The more autonomously an agent operates, the more ways it can go wrong unexpectedly.
3. **Context window vs. Information completeness** — LLMs have finite context windows. You can't feed them everything. You must choose what to include.
4. **Structured output vs. LLM creativity** — You need the LLM to produce machine-parseable JSON, but forcing strict structure can hurt reasoning quality.
5. **Self-correction vs. Infinite loops** — The agent should retry failures, but it must know when to give up.

Every major design decision in Singularity is a response to one of these tensions.

---

## 3. System Architecture Overview

The project has two execution modes that share the same skills, tools, and LLM layer.

### 3A. Legacy DAG Mode (`--depth`)

```
┌─────────────────────────────────────────────────────────────────┐
│                 CLI — agents/orchestrator/cli.py                │
└───────────────────────────────┬─────────────────────────────────┘
                                │ _legacy_run()
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│            RUNNER — agents/orchestrator/runner.py               │
│                                                                 │
│  ┌────────────┐  ┌──────────────┐  ┌────────────────────────┐  │
│  │  Planner   │  │   Executor   │  │    Gap Analyzer        │  │
│  │ (Round 0)  │  │  (Round 1-N) │  │  (after each round)    │  │
│  └────────────┘  └──────────────┘  └────────────────────────┘  │
└───────────────────────────────┬─────────────────────────────────┘
                                │
          ┌─────────────────────┼─────────────────────┐
          │                     │                     │
          ▼                     ▼                     ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│    PLANNER       │  │   EXECUTOR       │  │  ExecutionContext │
│ agents/planner/  │  │ agents/          │  │  models.py       │
│   planner.py     │  │ orchestrator/    │  │                  │
│                  │  │ executor.py      │  │ • results dict   │
│ • Calls Grok LLM │  │                  │  │ • node statuses  │
│ • Parses JSON    │  │ FallbackRouter   │  │ • credibility    │
│ • Returns Plan   │  │ execute_wave()   │  │ • citations      │
└──────────────────┘  └────────┬─────────┘  └──────────────────┘
                               ▼
              ┌────────────────────────────────┐
              │      SKILLS (SKILLS/)          │
              │  Tier 1: Retrieval (18)        │
              │  Tier 2: Analysis (18)         │
              │  Tier 3: Output (8)            │
              └────────────────────────────────┘
                               ▼
              ┌────────────────────────────────┐
              │           TOOLS (14)           │
              │  arXiv, PubMed, GitHub,        │
              │  HuggingFace, SEC EDGAR, ...   │
              └────────────────────────────────┘
```

### 3B. Phase 5 Strength-Based Pipeline (`--strength 1–10`)

The pipeline runs in four phases. Crucially, **planning (B) precedes retrieval (A)** — the
Retriever sees the finalised section tree and generates queries targeted at each actual section
topic rather than guessing from the top-level question alone.

```
CLI _strength_run()
        │
        ▼
  run_pipeline()  [agents/orchestrator/pipeline.py]
        │
        ├── Phase B: Structure Planning  ← FIRST
        │     3× ReportManagerAgent (parallel, diversity via assigned perspectives)
        │           └── ReportLeadAgent (synthesises → final ReportTree)
        │
        ├── Phase A: Retrieval  ← SECOND (tree-informed)
        │     Retriever receives the finalised tree; generates queries targeted
        │     at each section's evidence needs → skill fan-out → Qdrant
        │
        ├── Phase C: Writing (bottom-up)  ← THIRD
        │     ReportWorkerAgent per SectionNode
        │           ├── Call 1: Multi-Analysis (3 tier-2 skills, grok-3-mini)
        │           ├── Call 2: Section Write  (1 tier-3 skill, grok-4)
        │           └── Stores content + source_map on SectionNode (in-place)
        │                 ↓
        │     _format_report() → assembled Markdown + Reference List
        │
        └── Phase D: Polish  ← FOURTH
              Stage 1 — Python: normalise math delimiters, fix table syntax
              Stage 2 — LLM:   parallel section-by-section creative formatting
                                (tables, callouts, visual separators, flow)
```

### Module Inventory

| Module | Path | Responsibility |
|---|---|---|
| CLI Entry | `agents/orchestrator/cli.py` | Argument parsing, mode dispatch, `final_report.md` write |
| Runner (legacy) | `agents/orchestrator/runner.py` | DAG loop: plan → execute → gap-analyze → replan |
| Pipeline (Phase 5) | `agents/orchestrator/pipeline.py` | Phases A/B/C, assembles final Markdown + Reference List |
| Planner | `agents/planner/planner.py` | LLM call to generate/update DAG; `Planner`, `parse_plan()` |
| Domain Registry | `agents/planner/domain_registry.py` | Domain detection, fallback chains, audience rules |
| Executor | `agents/orchestrator/executor.py` | `FallbackRouter`, `execute_wave()`, `execute_node()` |
| Strength | `agents/orchestrator/strength.py` | `StrengthConfig` — maps 1–10 to retrieval counts, section range |
| Retriever | `agents/retriever/retriever.py` | LLM JSON plan of `skill_queries`; fan-out into Qdrant |
| Report Manager | `agents/report_manager/agent.py` | One hierarchical `ReportTree` proposal per instance |
| Report Lead | `agents/report_lead/agent.py` | Merges 3 proposals into the final `ReportTree` |
| Report Worker | `agents/report_worker/agent.py` | 2-call writer per section node; builds `source_map` for citations |
| Section Node | `agents/report_manager/section_node.py` | Data model: title, content, citations, `source_map` |
| Report Tree | `agents/report_manager/report_tree.py` | Tree model; `topological_levels()` for bottom-up writing |
| Models | `models.py` | All data contracts: `PlanNode`, `Plan`, `ExecutionContext`, `DocumentChunk`, etc. |
| Config | `agents/orchestrator/config.py` | All tunable constants (models, limits, paths) |
| Skills | `SKILLS/tier*/*/` | 36 skill implementations across 3 tiers |
| Tools | `tools/*.py` | 14 API connectors (arXiv, PubMed, GitHub, etc.) |
| Vector Store | `vector_store/client.py` | Qdrant client; in-memory fallback; topic cache |
| Budget | `context/budget.py` | `ContextBudgetManager` — context window budgeting |
| Citations | `citations/registry.py` | `CitationRegistry` — stable `[AuthorYYYY]` IDs (legacy mode) |
| LLM | `llm/*.py` | `GrokClient`, `GeminiClient`, `DeepSeekClient` |
| Domain Registry JSON | `agents/planner/domain_registry.json` | 11 domain bundles, fallback chains, skill metadata |

---

## 4. The Planner — LLM-Driven DAG Generation

The planner is the most interesting component. Its job is to take a research question and produce a structured execution plan — a DAG of tasks with skills, dependencies, acceptance criteria, and output slots.

### 4.1 What the Planner Produces

The planner outputs a JSON structure that looks like this (abbreviated):

```json
{
  "metadata": {
    "research_type": "exploratory",
    "core_goal": "Understand causes, detection, and mitigation of spurious correlations",
    "domain": "ml_research",
    "audience": "expert",
    "node_count": 15
  },
  "nodes": [
    {
      "node_id": "n1",
      "description": "Search academic literature for definitions and theoretical foundations",
      "skill": "academic_search",
      "depends_on": [],
      "acceptance": ["factual_grounding", "source_authority", "replication_status"],
      "parallelizable": true,
      "output_slot": "definitions_theory",
      "depth_override": "deep"
    },
    {
      "node_id": "n7",
      "description": "Perform claim verification on key findings from retrieval nodes",
      "skill": "claim_verification",
      "depends_on": ["n1", "n3", "n4"],
      "acceptance": ["factual_grounding", "cross_validation", "coherence"],
      "parallelizable": false,
      "output_slot": "verified_claims"
    }
  ]
}
```

Every field is meaningful:

- **`depends_on`**: Defines the DAG edges. The executor uses this to determine topological wave order.
- **`parallelizable`**: Hints to the executor whether this node can run concurrently with others in its wave.
- **`output_slot`**: A named key in the shared context where results are stored. Downstream nodes read from these slots.
- **`acceptance`**: Quality axes this node must satisfy. Used by the quality_check skill and gap analyzer.
- **`depth_override`**: Tells retrieval tools how many results to fetch (5/10/20 for shallow/standard/deep).
- **`synthesis_hint`**: Special instruction for output nodes — e.g., "Use technical terminology appropriate for experts."

### 4.2 The Planner System Prompt

The planner operates with a **534-line system prompt** (`planner/system_prompt.md`) that walks it through six phases of thinking:

| Phase | What Happens |
|---|---|
| **Phase 0** | Domain detection: match the problem against 11 domain bundles, load the appropriate skill subset |
| **Phase 1** | Intent disambiguation: classify research type (exploratory/comparative/confirmatory), extract core goal, constraints |
| **Phase 2** | Scope constraint: determine source types, depth, recency window, termination signal |
| **Phase 3** | Quality rubric: assign acceptance axes to each node (8 universal + 8 domain-specific axes) |
| **Phase 4** | DAG construction: build nodes with proper dependencies, assign skills, set parallelizability |
| **Phase 5** | Output formatting: emit JSON DAG + human-readable rubric summary + execution notes |

The system prompt contains the full **skill registry** (all 36 skills with descriptions, costs, latencies), the **domain registry** (11 domains with their preferred skills), and detailed instructions on DAG construction principles like:

- Retrieval nodes first (they have no dependencies)
- Verification nodes after retrieval (they need content to verify)
- Analysis nodes after verification (they synthesize verified material)
- Output nodes last (they format everything into a document)

### 4.3 Replanning

When a round completes with gaps (failed or partial nodes), the runner calls `planner.replan()`. This is a different prompt mode that:

1. Sends the planner the original problem statement
2. Sends a compact summary of all results so far (truncated to 350 chars each)
3. Sends the gap report: which nodes failed, why, what was attempted
4. Asks the planner to generate a new plan that fills the gaps

The replan can add new nodes, replace failed nodes with different skills, or add supplementary retrieval to shore up weak analyses.

### 4.4 Why Use an LLM as a Planner?

This is a significant design choice. You could hardcode research pipelines per domain. Why use an LLM?

**Advantages:**
- Handles arbitrarily varied research questions without pre-programming
- Can reason about dependencies (e.g., "verification needs retrieval first")
- Adapts to domain, depth, and audience dynamically
- Can replan based on natural-language gap descriptions

**Disadvantages:**
- Non-deterministic (two runs might produce different plans)
- Can produce invalid DAGs (cycles, missing dependencies, unknown skills)
- Adds latency and cost to every run
- Requires prompt engineering to produce consistent JSON

The system mitigates the risks with `plan.has_cycle()` checks, JSON extraction from fenced blocks, and schema validation.

---

## 5. The Orchestrator — Execution Engine

The runner (`orchestrator/runner.py`) is the brain that coordinates everything. Understanding it well is key to understanding agentic AI control flow.

### 5.1 The Main Loop

```python
for round_num in range(1, limits["rounds"] + 1):
    # 1. Topological sort → waves
    waves = plan.topological_waves()

    # 2. Execute all waves
    for wave_idx, wave in enumerate(waves):
        await execute_wave(wave, ctx, client, router, wave_idx)

    # 3. Analyze gaps
    gaps = run_gap_analysis(plan, ctx)

    # 4. Are we done?
    if check_termination(plan, ctx) and not gaps:
        break

    # 5. Hit the round limit?
    if round_num >= limits["rounds"]:
        break

    # 6. Snapshot failing hashes for loop detection
    for node in plan.nodes:
        if ctx.node_status[node.node_id] not in (OK, OK_DEGRADED):
            ctx.prior_hashes.add(node.description_hash())

    # 7. Replan
    _, plan = planner.replan(problem, ctx, gaps, round_num, depth)

    # 8. Loop detection — did the replan generate the same failing nodes?
    if detect_replan_loop(plan, ctx):
        break
```

**Depth limits** determine how many rounds are allowed and how large plans can be:

| Depth | Rounds | Max Nodes |
|---|---|---|
| shallow | 1 | 8 |
| standard | 3 | 15 |
| deep | 5 | 25 |

### 5.2 Topological Waves

The most important concept in the executor is **topological wave scheduling**. The DAG is sorted into layers where each layer contains only nodes whose dependencies have already been resolved.

```python
def topological_waves(self) -> list[list[PlanNode]]:
    remaining = {n.node_id: n for n in self.nodes}
    resolved: set[str] = set()
    waves: list[list[PlanNode]] = []

    while remaining:
        # A node is "ready" if all its deps are in resolved
        wave = [n for n in remaining.values()
                if all(d in resolved for d in n.depends_on)]
        if not wave:
            raise ValueError("DAG cycle detected")
        waves.append(wave)
        for n in wave:
            resolved.add(n.node_id)
            del remaining[n.node_id]

    return waves
```

For the spurious correlations plan, the waves were:
- **Wave 0**: n1, n2, n3, n4, n5, n6 (all retrieval, no deps) — 6 parallel
- **Wave 1**: n7, n8, n9 (verification/scoring, depend on retrieval) — 3 sequential
- **Wave 2**: n10 (meta_analysis, depends on n7/n8/n9)
- **Wave 3-7**: n11 through n15 (each depending on the previous)

Within each wave, `parallelizable=true` nodes run concurrently via `asyncio.gather()`.

### 5.3 The FallbackRouter

The `FallbackRouter` wraps every skill execution with a **fallback chain** and **retry logic**. It's one of the most important reliability mechanisms in the system.

```python
class FallbackRouter:
    async def execute(node, ctx, client):
        # Primary skill + up to 2 fallbacks from domain registry
        chain = [node.skill] + registry.get_fallback_chain(node.skill)
        # e.g., ["code_search", "web_search", "forum_search"]

        for attempt_idx, skill_name in enumerate(chain[:3]):
            skill = skill_map.get(skill_name)
            if skill is None:
                continue  # Skip unregistered skills

            for retry in range(3):  # 3 attempts per skill
                try:
                    result, status, credibility = await skill.run(node, ctx, client, registry)
                except Exception as exc:
                    # Exception: retry with backoff
                    await asyncio.sleep(RETRY_BACKOFF[retry])
                    continue

                if status != NodeStatus.FAILED:
                    # Success (even PARTIAL is accepted) — adjust credibility
                    credibility += CREDIBILITY_ADJ.get(fallback_level, 0.0)
                    return result, status, credibility, fallback_level

                # FAILED status: break retries, try next in chain
                break

        # All 3 skills exhausted
        return error_dict, NodeStatus.FAILED, 0.0, "exhausted"
```

The **credibility adjustment** encodes domain knowledge about source reliability: a result found through the primary academic search tool is more trustworthy than the same information scraped from a general web search or a forum post.

```python
CREDIBILITY_ADJ = {
    "primary":       0.0,   # No penalty — this is what was planned
    "fallback_1":   -0.05,  # Slight penalty — not the first choice
    "fallback_2":   -0.15,  # Larger penalty
    "web_search":   -0.10,  # General web is less authoritative
    "forum_search": -0.20,  # Forums are even less reliable
    "social_search":-0.25,  # Social media least reliable
}
```

### 5.4 Gap Analysis

After each round, the runner runs gap analysis: a scan of every node's status to identify what didn't work.

```python
def run_gap_analysis(plan, ctx) -> list[GapItem]:
    gaps = []
    for node in plan.nodes:
        status = ctx.node_status.get(node.node_id)

        if status == NodeStatus.PARTIAL:
            # Got some results but below the minimum threshold
            gaps.append(GapItem(node.node_id, IssueType.PARTIAL, detail))

        elif status in (NodeStatus.FAILED, NodeStatus.SKIPPED):
            # Nothing at all
            gaps.append(GapItem(node.node_id, IssueType.UNSATISFIED, error))

        elif status == NodeStatus.BLOCKED:
            # Auth/access error — retrying won't help
            gaps.append(GapItem(node.node_id, IssueType.BLOCKED, reason))

    return gaps
```

These `GapItem` objects are summarized and sent to the planner as a structured gap report for replanning.

---

## 6. Skills — The Three-Tier Task System

Skills are the unit of work in Singularity. Every node in the execution plan maps to a skill. There are 36 skills across three tiers.

### 6.1 Tier 1: Retrieval Skills (18 skills)

Retrieval skills fetch raw information from external sources. They are the foundation — without them, the analysis and output skills have nothing to work with.

**Base class**: `BaseRetrievalSkill`

```python
class BaseRetrievalSkill(SkillBase):
    min_ok: int = 2  # Minimum sources required for NodeStatus.OK

    async def _fetch(self, node: PlanNode) -> ToolResult:
        raise NotImplementedError  # Override to call a tool

    async def run(self, node, ctx, client, registry):
        result = await self._fetch(node)  # May raise

        if not result.ok:
            return self._fail(node, result.error)

        sources = list(result.sources)

        # Register every source in the citation registry
        if ctx.citation_registry:
            for src in sources:
                cid = ctx.citation_registry.register(src, self.name, node.output_slot)
                src["citation_id"] = cid

        n = len(sources)
        status = (NodeStatus.OK      if n >= self.min_ok else
                  NodeStatus.PARTIAL if n > 0           else
                  NodeStatus.FAILED)

        avg_cred = sum(s.get("credibility_base", 0.75) for s in sources) / n

        return output_dict, status, avg_cred
```

The key insight: **status is determined by how many sources were found**. This creates a clean, quantifiable quality threshold: if you found 0 results it's FAILED; if you found some but fewer than `min_ok` it's PARTIAL; otherwise it's OK.

**All 18 Retrieval Skills:**

| Skill | Tool | Credibility | Notes |
|---|---|---|---|
| `web_search` | DuckDuckGo + Tavily | 0.75–0.85 | .gov/.edu boosted |
| `academic_search` | arXiv + Semantic Scholar | 0.88–0.95 | Two sources merged |
| `clinical_search` | PubMed + ClinicalTrials.gov | 0.85–0.92 | Requires NCBI_EMAIL |
| `legal_search` | CourtListener | — | US case law |
| `financial_search` | SEC EDGAR + news | 1.0 (SEC) | Filings are authoritative |
| `patent_search` | Google Patents | — | — |
| `news_archive` | NewsAPI | — | — |
| `standards_search` | NIST + IEEE | — | Technical standards |
| `forum_search` | Reddit/StackOverflow | Low | Community knowledge |
| `video_search` | YouTube transcripts | — | Spoken content |
| `dataset_search` | HuggingFace Hub | 0.80–0.90 | Institution = 0.90 |
| `gov_search` | Government websites | High | Official sources |
| `book_search` | Google Books | — | — |
| `social_search` | Twitter/social | Low | Trend signals |
| `pdf_deep_extract` | PyPDF2 | — | Parses PDFs |
| `code_search` | GitHub | 0.70–0.90 | Stars boost credibility |
| `data_extraction` | Generic APIs | — | — |
| `multimedia_search` | Images/video | — | — |

**`academic_search` is unique** — it runs two tools in parallel and merges results with deduplication:

```python
class AcademicSearchSkill(BaseRetrievalSkill):
    async def run(self, node, ctx, client, registry):
        half = max(self._depth_n(node) // 2, 3)

        arxiv_res, s2_res = await asyncio.gather(
            ArxivTool().call_with_retry(node.description, max_results=half),
            SemanticScholarTool().call_with_retry(node.description, max_results=half),
            return_exceptions=True,
        )

        # Deduplicate by title prefix (first 50 chars)
        sources, seen = [], set()
        for res in (arxiv_res, s2_res):
            if isinstance(res, Exception) or not res.ok:
                continue
            for src in res.sources:
                key = src.get("title", "")[:50].lower()
                if key not in seen:
                    seen.add(key)
                    sources.append(src)
```

This is an example of **fan-out at the tool level** — running multiple sources in parallel and merging. Even if one tool fails, the skill can still succeed with partial results from the other.

### 6.2 Tier 2: Analysis Skills (18 skills)

Analysis skills use LLMs to reason about the retrieved content. They don't call external APIs — they process whatever is in the execution context.

**Base class**: `BaseAnalysisSkill`

```python
class BaseAnalysisSkill(SkillBase):
    PROMPT_FILE: str = ""  # e.g., "synthesis.md"

    async def run(self, node, ctx, client, registry):
        # 1. Load system prompt from prompts/{PROMPT_FILE}
        system_prompt = (prompts_dir / self.PROMPT_FILE).read_text()

        # 2. Build context from upstream nodes
        upstream = ContextBudgetManager().build_context(node, ctx)

        # 3. Construct user message
        user_message = f"""## Node
node_id: {node.node_id}
skill: {node.skill}
description: {node.description}
acceptance_axes: {', '.join(node.acceptance)}

## Upstream Context
{upstream}"""

        # 4. Call LLM (via asyncio.to_thread to not block event loop)
        raw = await asyncio.to_thread(
            client.generate_text,
            prompt=user_message,
            system_prompt=system_prompt,
            temperature=0.3,
        )

        # 5. Parse JSON from response
        data = self._extract_json(raw)

        # 6. Status is based on LLM-reported confidence
        output = AnalysisOutput(
            summary=data.get("summary", ""),
            findings=data.get("findings", []),
            confidence=float(data.get("confidence", 0.5)),
            ...
        )

        status = NodeStatus.OK if output.confidence >= 0.70 else NodeStatus.PARTIAL
        return output.to_dict(), status, output.confidence
```

The LLM evaluates its own confidence and reports it in the JSON output. The system trusts this self-assessment: confidence ≥ 0.70 → OK, < 0.70 → PARTIAL. This is a form of **LLM self-reflection** — asking the model to assess how well it answered rather than having external verification (though the claim_verification skill provides cross-checking).

**`_extract_json` — Robust JSON Parsing:**

LLMs frequently wrap JSON in markdown code fences or mix text with JSON. This parser handles both cases:

```python
@staticmethod
def _extract_json(text: str) -> dict:
    # Try: ```json\n{...}\n```
    m = re.search(r"```json\s*\n(.*?)\n```", text, re.DOTALL)
    if m:
        return json.loads(m.group(1))

    # Try: raw JSON object at start of text
    stripped = text.strip()
    if stripped.startswith("{"):
        decoder = json.JSONDecoder()
        obj, _ = decoder.raw_decode(stripped)
        return obj

    raise ValueError(f"No JSON found: {stripped[:200]}")
```

**All 18 Analysis Skills:**

| Skill | Prompt File | What It Does |
|---|---|---|
| `synthesis` | synthesis.md | Combines sources into themes with citations |
| `comparative_analysis` | comparative_analysis.md | Compares entities along axes |
| `gap_analysis` | gap_analysis.md | Identifies coverage gaps |
| `quality_check` | quality_check.md | Evaluates acceptance criteria |
| `contradiction_detect` | contradiction_detect.md | Finds disagreements between sources |
| `claim_verification` | claim_verification.md | Verifies claims against evidence |
| `causal_analysis` | causal_analysis.md | Maps cause-effect relationships |
| `statistical_analysis` | statistical_analysis.md | Analyses statistical findings |
| `meta_analysis` | meta_analysis.md | Aggregates effect sizes (clinical focus) |
| `trend_analysis` | trend_analysis.md | Identifies trends over time |
| `timeline_construct` | timeline_construct.md | Builds chronological narratives |
| `hypothesis_gen` | hypothesis_gen.md | Generates testable hypotheses |
| `entity_extraction` | entity_extraction.md | Extracts key entities (people, orgs, concepts) |
| `citation_graph` | citation_graph.md | Builds citation network |
| `sentiment_cluster` | sentiment_cluster.md | Clusters by sentiment |
| `credibility_score` | credibility_score.md | Aggregates source trustworthiness |
| `translation` | translation.md | Translates content |
| `fallback_router` | fallback_router.md | Routes to alternate skills |

### 6.3 Tier 3: Output Skills (8 skills)

Output skills are the final layer — they take all the analysed content and format it into a specific document type.

**Base class**: `BaseOutputSkill`

```python
class BaseOutputSkill(SkillBase):
    PROMPT_FILE: str = ""
    format_type: OutputFormat = "report"

    async def run(self, node, ctx, client, registry):
        system_prompt = (prompts_dir / self.PROMPT_FILE).read_text()
        upstream = ContextBudgetManager().build_context(node, ctx)

        # Read audience from context (set by planner)
        audience = getattr(ctx, "audience", "") or "general"

        user_message = f"audience: {audience}\n\n## Upstream Context\n{upstream}"

        raw = await asyncio.to_thread(client.generate_text, ...)
        data = self._extract_json(raw)

        # Build Markdown from findings list
        sections = []
        if data.get("summary"):
            sections.append(f"## Executive Summary\n\n{data['summary']}")
        for item in data.get("findings", []):
            sections.append(f"## {item['section']}\n\n{item['content']}")

        content = "\n\n".join(sections)

        output = OutputDocument(
            format=self.format_type,
            content=content,
            audience=audience,
            ...
        )

        # Status based on LLM confidence
        status = NodeStatus.OK if confidence >= 0.70 else NodeStatus.PARTIAL
```

**All 8 Output Skills:**

| Skill | Format Type | Primary Use |
|---|---|---|
| `report_generator` | report | Full research report (600–3000+ words) |
| `exec_summary` | exec_summary | 150-word executive summary |
| `bibliography_gen` | bibliography | Formatted citations in APA/IEEE/Vancouver |
| `decision_matrix` | decision_matrix | Structured comparison table |
| `explainer` | explainer | Accessible non-expert explanation |
| `annotation_gen` | annotations | Annotated content with commentary |
| `visualization_spec` | visualization_spec | Chart/graph specifications for rendering |
| `knowledge_delta` | knowledge_delta | What's new vs. prior knowledge |

---

## 7. Tools — The Data Source Layer

Tools are the lowest level of the system — raw connectors to external APIs. They don't know about skills, context, or the DAG. They just fetch data.

### 7.1 ToolBase and ToolResult

```python
@dataclass
class ToolResult:
    content: str             # Primary extracted text (for LLM consumption)
    sources: list[dict]      # Structured source records
    credibility_base: float  # 0-1 baseline credibility
    raw: Any = None          # Raw API response (debugging)
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None

class ToolBase:
    async def call(query: str, **kwargs) -> ToolResult:
        raise NotImplementedError

    async def call_with_retry(query: str, max_retries: int = 2, **kwargs) -> ToolResult:
        # Tries up to 3 times with exponential backoff (1s, 2s)
        # NEVER raises — returns ToolResult.failure(error) on exhaustion
```

The `call_with_retry` contract is critical: **tools never raise exceptions**. They always return a `ToolResult`, and the caller checks `.ok`. This prevents tool failures from cascading into unhandled exceptions.

### 7.2 Credibility Scoring at the Source Level

Each tool assigns credibility scores based on source-specific signals:

**ArxivTool:**
```python
credibility = 0.95 if paper.is_published else 0.88  # Preprints get penalized
```

**SemanticScholarTool:**
```python
citation_boost = min(0.05, (paper.citation_count / 1000) * 0.05)
credibility = 0.90 + citation_boost  # More cited = more trusted
```

**GitHubTool:**
```python
stars_boost = min(0.20, (repo.stargazers_count / 1000) * 0.20)
credibility = 0.70 + stars_boost  # More starred = more trusted
```

**SEC EdgarTool:**
```python
credibility = 1.0  # Government financial filings are authoritative
```

**WebFetchTool:**
```python
credibility = 0.85 if ".gov" in url or ".edu" in url else 0.75
```

**DatasetHubTool:**
```python
credibility = 0.90 if author in INSTITUTIONS else 0.80
# INSTITUTIONS = {"google", "microsoft", "anthropic", "allenai", ...}
```

This credibility layer propagates all the way up: tool → skill → executor → context. The final report footer shows `Mean source credibility: 0.63 / 1.00`.

### 7.3 The `_to_query` Transformation

One bug we fixed was that tools were receiving full node descriptions as search queries:

> "Search datasets and benchmarks highlighting causes of spurious correlations, such as data biases and confounding variables"

This is an instruction to the agent, not a search query. GitHub and HuggingFace Hub use keyword/text matching, so this verbose phrase returns 0 results.

The fix: a `_to_query()` helper on `BaseRetrievalSkill` that extracts the core topic:

```python
def _to_query(self, description: str, max_words: int = 8) -> str:
    # Find the semantic subject after "for", "of", "about", etc.
    m = re.search(
        r'\b(?:for(?:\s+examples?\s+of)?|about|on|of|highlighting|covering)\s+(.+)',
        description, re.IGNORECASE,
    )
    topic = m.group(1) if m else description
    # Cut at first comma to drop "such as ..." clauses
    topic = re.sub(r'[,;:].*', '', topic).strip()
    return " ".join(topic.split()[:max_words])
```

Result:
- Input: "Search datasets and benchmarks highlighting causes of spurious correlations, such as data biases..."
- Output: `"spurious correlations"`

---

## 8. Context Management — Feeding the Right Information

This is one of the subtlest but most important problems in agentic AI. LLMs have a finite context window. In a 15-node pipeline, by the time you reach the report_generator node, there might be 100,000+ characters of upstream results. You can't fit everything. You must be selective.

### 8.1 The ContextBudgetManager

```python
class ContextBudgetManager:
    MAX_DIRECT_CHARS: int  = 12000  # Nodes this node directly depends on
    MAX_INDIRECT_CHARS: int = 350   # All other resolved nodes (summaries)
    MAX_TOTAL_CHARS: int   = 32000  # Hard cap

    def build_context(self, node: PlanNode, ctx: ExecutionContext) -> str:
        direct_slots = set(node.depends_on)  # Immediate dependencies

        sections = []
        total = 0

        # Direct dependencies: full content
        for slot, result in ctx.results.items():
            if slot in direct_slots:
                text = json.dumps(result)[:MAX_DIRECT_CHARS]
                sections.append(f"### {slot} (direct)\n{text}")
                total += len(text)

        # Indirect: summaries only, sorted by credibility (best first)
        indirect = sorted(
            [(slot, result) for slot, result in ctx.results.items()
             if slot not in direct_slots],
            key=lambda x: ctx.credibility_scores.get(x[0], 0),
            reverse=True
        )

        for slot, result in indirect:
            if total >= MAX_TOTAL_CHARS:
                break
            summary = textwrap.shorten(json.dumps(result), width=MAX_INDIRECT_CHARS)
            sections.append(f"### {slot} (indirect)\n{summary}")
            total += len(summary)

        # Always include synthesis_hint
        if node.synthesis_hint:
            sections.append(f"### synthesis_hint\n{node.synthesis_hint}")

        return "\n\n".join(sections)
```

### 8.2 The Design Principles Behind This

**Direct vs. Indirect**: A node directly depends on certain upstream nodes (declared in `depends_on`). Those get full content — the LLM needs them to do its work. Everything else is background context: summarized to 350 chars to give orientation without overwhelming.

**Credibility-ranked dropping**: When the total budget would be exceeded, the least credible indirect sources are dropped first. This ensures that if tradeoffs must be made, higher-quality information survives.

**Why 32,000 chars?**: At roughly 4 chars/token, this is ~8,000 tokens. Most LLMs handle 128K+ tokens, but the budget is conservative to manage API costs and ensure coherent responses.

### 8.3 The result_summary() for Replanning

The runner also needs to summarize all results for the replanning prompt. `ExecutionContext.result_summary()` handles this:

```python
def result_summary(self) -> dict[str, str]:
    out = {}
    for slot, val in self.results.items():
        text = json.dumps(val, default=str)
        score = self.credibility_scores.get(slot, 1.0)
        summary = textwrap.shorten(text, width=350)  # 350 chars max
        if score < 0.85:
            summary += f" [credibility: {score:.2f}]"
        out[slot] = summary
    return out
```

Low-credibility results get a visible credibility annotation, signaling to the replan LLM that this source is less reliable and may need supplementation.

---

## 9. Citation & Credibility System

Research is only as good as its sources. The citation system provides:
1. A unique stable ID for every source (`[AuthorYYYY]`)
2. A bibliography formatted in any citation style
3. A credibility score for every source that propagates through the system

### 9.1 CitationRegistry

```python
class CitationRegistry:
    def register(self, source: dict, registered_by: str, output_slot: str) -> str:
        url = source.get("url", "")

        # Deduplicate by URL
        if url in self._by_url:
            return self._by_url[url].citation_id

        # Generate [AuthorYYYY] style ID
        cid = self._generate_id(source)

        # Store
        record = CitationRecord(
            citation_id=cid,
            title=source.get("title", ""),
            url=url,
            date=source.get("date"),
            source_type=source.get("source_type", "web"),
            credibility_base=source.get("credibility_base", 0.75),
            authors=source.get("authors", []),
            registered_by=registered_by,
            output_slot=output_slot,
        )
        self._by_id[cid] = record
        self._by_url[url] = record
        return cid

    def _generate_id(self, source: dict) -> str:
        authors = source.get("authors", [])
        year = (source.get("date") or "")[:4] or "XXXX"

        if authors:
            last_name = authors[0].split()[-1]  # "Smith"
        else:
            # Fallback: CamelCase the title
            words = source.get("title", "Unknown").split()[:3]
            last_name = "".join(w.capitalize() for w in words)

        base = f"{last_name}{year}"  # "Smith2024"

        # Handle collisions with a-z suffix
        if base not in self._by_id:
            return f"[{base}]"

        for suffix in "abcdefghijklmnopqrstuvwxyz":
            candidate = f"{base}{suffix}"
            if candidate not in self._by_id:
                return f"[{candidate}]"
```

### 9.2 Bibliography Formatting

```python
def format_bibliography(self, style: str = "APA") -> str:
    lines = []
    for cid, rec in sorted(self._by_id.items()):
        if style == "APA":
            authors = ", ".join(rec.authors[:3])
            if len(rec.authors) > 3:
                authors += " et al."
            year = rec.date[:4] if rec.date else "n.d."
            lines.append(f"{authors} ({year}). {rec.title}. {rec.url}")
        elif style == "IEEE":
            # [1] J. Smith, "Title," Year. URL
            ...
    return "\n".join(lines)
```

### 9.3 Credibility Propagation Flow

```
Tool assigns credibility_base
    ↓
BaseRetrievalSkill averages across sources
    ↓
FallbackRouter adjusts by fallback level
    ↓
ExecutionContext stores in credibility_scores[output_slot]
    ↓
ContextBudgetManager sorts indirect context by credibility
    ↓
result_summary() annotates low-credibility slots
    ↓
Final report footer: Mean source credibility: X.XX
```

---

## 10. LLM Integration Layer

The system is LLM-agnostic by design. Any model that can do text completion can be swapped in.

### 10.1 BaseLLMClient

```python
class BaseLLMClient:
    def generate_text(
        prompt: str,
        system_prompt: str,
        temperature: float = 0.5,
        max_tokens: int | None = None,
    ) -> str:
        raise NotImplementedError

    def generate_structured(
        prompt: str,
        system_prompt: str,
        schema: type[BaseModel],
        temperature: float = 0.5,
    ) -> BaseModel:
        raise NotImplementedError
```

### 10.2 GrokClient (Default Planner)

The planner uses `GrokClient(model_name="grok-3-mini")` — xAI's Grok model via the OpenAI-compatible SDK:

```python
class GrokClient(BaseLLMClient):
    def __init__(self, model_name: str = "grok-beta", api_key: str | None = None):
        key = api_key or os.getenv("XAI_API_KEY")
        self.client = OpenAI(
            api_key=key,
            base_url="https://api.x.ai/v1",
        )
        self.model_name = model_name

    def generate_text(self, prompt, system_prompt, temperature=0.5, max_tokens=None):
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content
```

This is an important architectural point: because `GrokClient` uses the OpenAI SDK with a custom `base_url`, **any OpenAI-compatible API** can be used as a drop-in by creating a client with a different base URL. This is the standard pattern for LLM abstraction.

### 10.3 Why async.to_thread for LLM Calls

The executor runs the entire pipeline with `asyncio`. But all three LLM clients use **synchronous HTTP calls** (via the OpenAI/Google/DeepSeek SDKs). Running sync calls directly in an async context would block the event loop, preventing parallel wave execution.

The fix:
```python
raw = await asyncio.to_thread(
    client.generate_text,
    prompt=user_message,
    system_prompt=system_prompt,
    temperature=0.3,
)
```

`asyncio.to_thread()` runs the sync function in a thread pool executor, so the event loop remains unblocked. This is the standard Python pattern for integrating sync code into async workflows.

### 10.4 The LLM Router

```python
def get_llm_client(model_id: str, api_key: str | None = None) -> BaseLLMClient:
    if model_id.startswith("deepseek-"):
        return DeepSeekClient(model_name=model_id, api_key=api_key)
    if model_id.startswith("grok-"):
        return GrokClient(model_name=model_id, api_key=api_key)
    return GeminiClient(model_name=model_id, api_key=api_key)
```

Switching models requires only changing `PLANNER_MODEL` in `config.py`. The same skills, prompts, and execution engine work with any model.

---

## 11. Domain Registry — Making the Agent Domain-Aware

One of the most powerful features of Singularity is that it adapts its behavior based on the **domain** of the research question. A medical research question gets different tools, different quality standards, and different citation style than a financial analysis question.

### 11.1 Domain Detection

```python
def detect_domain(self, problem: str) -> tuple[str, str]:
    problem_lower = problem.lower()

    # Score each domain by signal keyword matches
    scores = {
        key: sum(1 for signal in domain["detection_signals"] if signal in problem_lower)
        for key, domain in self._data["domains"].items()
        if key != "general"
    }

    scores = {k: v for k, v in scores.items() if v > 0}

    if not scores:
        return "general", "low"

    top = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    # Tie → fall back to general (ambiguous domain)
    if len(top) >= 2 and top[0][1] == top[1][1]:
        return "general", "low"

    best_key, best_score = top[0]
    confidence = "high" if best_score >= 3 else "medium" if best_score >= 2 else "low"
    return best_key, confidence
```

For "research about spurious correlations in machine learning":
- "machine" doesn't appear in signals
- "learning" doesn't appear
- But the planner gets the domain context passed separately, so it planned `ml_research`

Note: the domain detection feeds into the planner's context, not just the CLI output. The planner uses the domain to select which skill subset to use.

### 11.2 The 11 Domain Bundles

Each domain has a structured configuration:

```json
"ml_research": {
    "label": "ML / AI Research",
    "detection_signals": ["model", "dataset", "benchmark", "training", "neural", "LLM", "transformer", ...],
    "default_audience": "expert",
    "default_output_format": "academic_paper",
    "source_skills": {
        "primary": ["academic_search", "code_search", "dataset_search"],
        "secondary": ["web_search", "video_search", "forum_search"]
    },
    "analysis_skills": {
        "primary": ["comparative_analysis", "gap_analysis", "citation_graph"],
        "secondary": ["trend_analysis", "statistical_analysis", "hypothesis_gen"]
    },
    "output_skills": ["report_generator", "bibliography_gen", "visualization_spec"],
    "quality_axes": {
        "universal": ["source_authority", "cross_validation", "recency", "depth"],
        "domain_specific": ["replication_status", "methodological_soundness"]
    },
    "recency_window_years": 2
}
```

### 11.3 Fallback Chains

Every skill has a fallback chain — if the primary skill fails, what should be tried next?

```json
"fallback_chains": {
    "academic_search":  ["web_search", "book_search", "forum_search"],
    "code_search":      ["web_search", "forum_search"],
    "dataset_search":   ["academic_search", "web_search"],
    "clinical_search":  ["academic_search", "gov_search", "web_search"],
    "financial_search": ["news_archive", "web_search", "gov_search"],
    "legal_search":     ["gov_search", "academic_search", "pdf_deep_extract"]
}
```

The fallback chains are designed with domain knowledge:
- If GitHub fails for `code_search`, try general web search or forums (where code discussions happen)
- If HuggingFace fails for `dataset_search`, try academic papers or web (which may describe datasets)
- If PubMed fails for `clinical_search`, try academic search (arXiv has medical preprints) then government health sites

---

## 12. Contracts — Data Shape Guarantees

The `contracts/skill_contracts.py` module defines Pydantic models for every type of output in the system. This is an important reliability pattern.

### 12.1 Why Contracts?

Without contracts, the data flowing between skills is just a `dict[str, Any]`. When a Tier 2 skill reads data from a Tier 1 skill, it doesn't know what fields to expect. This leads to:
- `KeyError` crashes when an expected field is missing
- Silent `None` bugs when a field has the wrong type
- Drift over time as skills are updated independently

With Pydantic contracts:
- Every field is explicitly typed
- Validation happens at creation time
- If a skill produces malformed output, it fails loudly with a clear error
- Documentation is built into the model definition

### 12.2 The Contracts

**SourceRecord** (individual source from Tier 1):
```python
class SourceRecord(BaseModel, frozen=True):
    citation_id: str           # "[Smith2024]"
    title: str
    url: str
    snippet: str               # ≤300 chars of content
    date: str | None           # ISO 8601
    source_type: SourceType    # "academic" | "web" | "gov" | "code" | "dataset" | ...
    credibility_base: float    # 0.0 – 1.0
    authors: list[str] = []
    metadata: dict = {}
```

**RetrievalOutput** (Tier 1 skill output):
```python
class RetrievalOutput(BaseModel):
    skill_name: str
    sources: list[SourceRecord]
    query_used: str
    result_count: int
    coverage_notes: str        # "20 results found" or "3 results — below minimum"
    fallback_used: bool
```

**AnalysisOutput** (Tier 2 skill output):
```python
class AnalysisOutput(BaseModel):
    skill_name: str
    summary: str               # 2-4 sentence overview
    findings: list[dict]       # Skill-specific structure
    citations_used: list[str]  # ["[Smith2024]", "[Jones2023]"]
    confidence: float          # 0.0 – 1.0 (self-reported by LLM)
    coverage_gaps: list[str]   # What was missing
    upstream_slots_consumed: list[str]
```

**QualityReport** (quality_check skill):
```python
class AxisResult(BaseModel):
    axis: str                 # e.g., "source_authority"
    passed: bool
    score: float              # 0.0 – 1.0
    reason: str
    threshold: float          # What score is required to pass

class QualityReport(BaseModel):
    node_id: str
    axes_evaluated: list[str]
    results: dict[str, AxisResult]
    overall_pass: bool
    overall_score: float
    remediation_suggestion: str | None
```

**OutputDocument** (Tier 3 skill output):
```python
class OutputDocument(BaseModel):
    skill_name: str
    format: OutputFormat       # "report" | "exec_summary" | ...
    content: str               # Full Markdown content
    audience: str
    word_count: int            # Auto-computed by validator
    citations_included: list[str]
    coverage_gaps_disclosed: list[str]
    disclaimer_present: bool
    language: str
```

---

## 13. Bugs We Hit and How We Fixed Them

This section is the most valuable part for learning agentic AI design — real bugs that emerged from running the system, their root causes, and the fixes. Each bug reveals a general principle.

### Bug 1: Loop Detection Misfired After Round 1 (Critical)

**Symptom:**
```
[WARN] Replan loop detected on ['n2', 'n3', 'n10', 'n11', 'n14'] — stopping with partial results.
```
This fired after Round 1, before any replanning had happened. A `deep` run that was supposed to use 5 rounds only ran 1.

**Root Cause:**

The loop detector (`detect_replan_loop`) is supposed to catch *infinite replanning cycles* — situations where the planner keeps generating the same failing nodes repeatedly. Its logic:

```python
def detect_replan_loop(plan: Plan, ctx: ExecutionContext) -> list[str]:
    return [
        node.node_id for node in plan.nodes
        if node.description_hash() in ctx.prior_hashes
        and ctx.node_status[node.node_id] not in (OK, OK_DEGRADED)
    ]
```

And `ctx.prior_hashes` was populated in `ctx.record()`:

```python
def record(self, node, result, status, ...):
    self.results[node.output_slot] = result
    self.node_status[node.node_id] = status
    self.credibility_scores[node.output_slot] = ...
    self.prior_hashes.add(node.description_hash())  # ← BUG: adds ALL nodes
```

The problem: `record()` is called for every executed node, including successful ones. After Round 1 completes, **all 15 nodes** have their hashes in `prior_hashes`. Then `detect_replan_loop` checks: "are any failing nodes in `prior_hashes`?" — yes, all 5 failing ones are there, because they were just executed.

This is a logic error about **when** the hash should be recorded. The intent was "track nodes that failed so we can detect if a replan regenerates them." The implementation was "track all executed nodes."

**Fix:**

Two changes:
1. Remove the `prior_hashes.add()` from `ctx.record()`
2. In `runner.py`, explicitly add failing node hashes to `prior_hashes` immediately before replanning (not during execution)

```python
# Snapshot failing hashes BEFORE replanning
for node in plan.nodes:
    s = ctx.node_status.get(node.node_id)
    if s not in (NodeStatus.OK, NodeStatus.OK_DEGRADED, None):
        ctx.prior_hashes.add(node.description_hash())

# Now replan
_, plan = planner.replan(...)

# THEN check if the new plan repeats the same failures
looping = detect_replan_loop(plan, ctx)
```

Now the flow is correct:
- Round 1: execute → gap analysis → save failing hashes → replan → loop-check the NEW plan
- Round 2: execute new plan → if same nodes still fail, their hashes ARE in `prior_hashes` → loop detected

**General Principle:** *State management in multi-round agents is subtle. Be explicit about when and why you update shared state. Implicit updates (adding to `prior_hashes` on every `record()`) create hard-to-see coupling between mechanisms.*

---

### Bug 2: Fallback Chain Never Activated (High)

**Symptom:** `code_search` and `dataset_search` returned `FAILED`, and the fallback chain (`web_search`, `forum_search`) was never tried.

**Root Cause:**

`FallbackRouter.execute()` was exception-driven:

```python
for retry in range(3):
    try:
        result, status, credibility = await skill.run(...)
        fallback_level = ...
        return result, status, credibility, fallback_level  # Returns on ANY result
    except Exception as exc:
        # Retry...
```

The problem: `BaseRetrievalSkill.run()` **catches all exceptions internally** and returns `(dict, NodeStatus.FAILED, 0.0)` — a clean return value, not a raised exception. From `FallbackRouter`'s perspective, the skill "succeeded" (no exception) — it got a return value. It returned that FAILED status without trying the fallback.

Two systems with incompatible assumptions:
- **FallbackRouter** assumed: exceptions = failure, needs fallback
- **BaseRetrievalSkill** assumed: return FAILED status = failure, caller should handle it

Neither was wrong in isolation. The mismatch was in the interface contract between them.

**Fix:**

Change `FallbackRouter` to check the **returned status**, not just exceptions:

```python
for retry in range(3):
    try:
        result, status, credibility = await skill.run(...)
    except Exception as exc:
        # Exception-based failure: retry with backoff
        await asyncio.sleep(backoff)
        continue

    if status != NodeStatus.FAILED:
        # Success (even PARTIAL counts)
        return result, status, credibility, fallback_level

    # Status-based failure: don't retry, try next skill in chain
    last_error = result.get("error", "skill returned FAILED")
    break  # Exit retry loop, advance to next fallback
```

**General Principle:** *When two components communicate, ensure they agree on what "failure" means. Is it an exception? A return value? An error field? Mismatched error conventions are a common source of silent failures in multi-component systems.*

---

### Bug 3: Verbose Node Descriptions as Search Queries (Medium)

**Symptom:** `code_search` and `dataset_search` returned 0 results despite valid queries.

**Root Cause:**

The planner generates descriptive node tasks like:

> "Search code repositories and open-source ML projects for examples of spurious correlations in real-world applications"

This is passed directly to `GitHubTool().call_with_retry(node.description, ...)`. GitHub's search engine received a 17-word sentence and returned 0 repositories. It's a keyword search engine, not a semantic one.

The fundamental mismatch: **node descriptions are instructions to the agent, not queries for external APIs**.

**Fix:**

Add `_to_query()` to `BaseRetrievalSkill` to extract the semantic subject:

```python
def _to_query(self, description: str, max_words: int = 8) -> str:
    # Find content after prepositions like "for examples of", "about", "on"
    m = re.search(
        r'\b(?:for(?:\s+examples?\s+of)?|about|on|of|highlighting|covering)\s+(.+)',
        description, re.IGNORECASE,
    )
    topic = m.group(1) if m else description
    # Cut at commas to drop "such as X, Y, Z" expansions
    topic = re.sub(r'[,;:].*', '', topic).strip()
    return " ".join(topic.split()[:max_words])
```

Now `code_search` passes `"spurious correlations in real-world applications"` instead of the full sentence.

**General Principle:** *The same information serves different audiences differently. An instruction to an agent is not the same as a query to a search API. When information passes between subsystems with different semantics, explicitly transform it rather than passing it verbatim.*

---

### Bug 4: Cascading PARTIAL States (Medium)

**Symptom:** `meta_analysis` (n10), `causal_analysis` (n11), and `visualization_spec` (n14) all returned PARTIAL even though they are LLM-based skills with no external API dependencies.

**Root Cause:** This is a cascade from Bug 2 and Bug 3. With `dataset_search` (n3) failing:

- n3 (dataset_search) → FAILED
- n7 (claim_verification) depends on n1, n3, n4 → gets degraded context (n3 missing)
- n10 (meta_analysis) depends on n7, n8, n9 → LLM receives incomplete upstream data
- LLM correctly self-reports `confidence: 0.62` (below 0.70 threshold) → PARTIAL
- n11 depends on n10 → inherits the degradation
- n14 depends on n13 depends on n11/n10 → cascade propagates

This isn't really a bug in n10/n11/n14 — the LLM correctly assessed that it had incomplete data. The root cause is that n3 failed and the fallback didn't activate.

**Fix:** By fixing Bug 2 (fallback chain activation) and Bug 3 (query extraction), n3 now retrieves datasets via `academic_search` fallback. The context flowing into n10 is complete, and its confidence rises above 0.70.

**General Principle:** *In a DAG pipeline, failures cascade silently through dependent nodes. When debugging, always trace failures back to their source rather than fixing symptoms. PARTIAL nodes are often downstream victims of root-cause FAILED nodes.*

---

### Bug 5: Report Audience Hardcoded to "General" (Low)

**Symptom:** The final report was calibrated for a general audience despite the planner specifying `"audience": "expert"` in the plan metadata.

**Root Cause:**

`BaseOutputSkill.run()` read the audience from:
```python
audience = ctx.results.get('metadata', {}).get('audience', 'general')
```

But there is no `'metadata'` key in `ctx.results`. The plan metadata (`plan.metadata.audience`) is a separate Python object — it's never stored in the results dictionary. So `ctx.results.get('metadata', {})` always returns `{}`, and `audience` always falls back to `"general"`.

**Fix (two parts):**

1. Add `audience: str = ""` field to `ExecutionContext`
2. Set it in `runner.py` immediately after planning: `ctx.audience = plan.metadata.audience`
3. Read it in `BaseOutputSkill`: `audience = getattr(ctx, "audience", "") or "general"`

**General Principle:** *When information is needed in multiple places, store it in a shared, accessible location. Don't assume it can be reconstructed from indirect paths. The `ExecutionContext` is the single source of truth for the run — metadata about the run belongs there.*

---

## 14. End-to-End Data Flow Walkthrough

Let's trace a single source through the entire system, from API call to the final report.

**Input:** "research about spurious correlations in machine learning"

### Step 1: arXiv Paper Discovered

`ArxivTool.call()` returns:
```python
ToolResult(
    content="[Smith2024] Complexity Matters: Spurious Correlations in Neural Networks\n...",
    sources=[{
        "title": "Complexity Matters: Spurious Correlations in Neural Networks",
        "url": "http://arxiv.org/abs/2401.12345v1",
        "snippet": "We show that deep networks exploit spurious features when they are simpler than causal features...",
        "date": "2024-01-15",
        "source_type": "academic",
        "credibility_base": 0.95,
        "authors": ["Smith, J.", "Jones, K."],
    }],
    credibility_base=0.95,
)
```

### Step 2: Citation Registered

`BaseRetrievalSkill.run()` registers the source:
```python
cid = ctx.citation_registry.register(source, "academic_search", "definitions_theory")
# → "[Smith2024]"
source["citation_id"] = "[Smith2024]"
```

### Step 3: Result Stored

```python
ctx.record(node=n1, result={
    "skill_name": "academic_search",
    "sources": [{"title": "Complexity Matters...", "citation_id": "[Smith2024]", ...}],
    "result_count": 12,
    "coverage_notes": "12 result(s) found",
    ...
}, status=NodeStatus.OK, credibility=0.91)
```

### Step 4: Context Built for Synthesis

When `synthesis` (n13) runs, `ContextBudgetManager.build_context()` assembles:
```
### definitions_theory (direct)
{"skill_name": "academic_search", "sources": [{"title": "Complexity Matters...",
"citation_id": "[Smith2024]", "snippet": "We show that deep networks..."}], ...}

### verified_claims (direct)
{"summary": "Claims about spurious feature exploitation are well-supported...", ...}

### detection_methods (indirect)
{"skill_name": "academic_search", "sources": [...], "result_count": 15...} [truncated]
```

### Step 5: LLM Synthesizes

The synthesis LLM receives the upstream context and the synthesis prompt. It produces:
```json
{
  "summary": "Spurious correlations arise when models exploit non-causal features...",
  "findings": [
    {"section": "Causes", "content": "Neural networks tend to exploit spurious features when they are computationally simpler [Smith2024]..."},
    {"section": "Detection", "content": "Statistical testing and feature attribution methods can expose spurious patterns..."}
  ],
  "citations_used": ["[Smith2024]", "[Jones2023]"],
  "confidence": 0.82
}
```

### Step 6: Report Generated

`report_generator` assembles the final document:
```markdown
## Executive Summary

Spurious correlations in ML represent a fundamental challenge where models exploit
statistical regularities that don't reflect causal relationships...

## Causes

Neural networks tend to exploit spurious features when they are computationally
simpler than the true causal features [Smith2024]. This creates a shortcut
learning problem...
```

### Step 7: Final Report Written

The CLI assembles:
```markdown
# Research Report

**Query:** research about spurious correlations in machine learning

---

[Report content from report_generator]

---

## Coverage Gaps

- Limited code examples from repositories

---

## References

Smith, J., Jones, K. (2024). Complexity Matters: Spurious Correlations in Neural Networks.
http://arxiv.org/abs/2401.12345v1

---

*Mean source credibility: 0.82 / 1.00*
```

---

## 15. Key Agentic AI Patterns Used in This Project

This project is a working implementation of many of the most important patterns in modern agentic AI. Understanding these patterns is the core lesson.

### 15.1 DAG Orchestration

The execution plan is a directed acyclic graph. Nodes are tasks. Edges are dependencies. This allows:
- **Parallelism**: Tasks with no unsatisfied dependencies run simultaneously
- **Dependency tracking**: Tasks that need upstream results wait for them
- **Partial execution**: The system can proceed with successful nodes even when some fail

DAG orchestration is used in nearly every production AI workflow system: LangGraph, Prefect, Airflow, Apache Beam.

### 15.2 Tool Use

Skills call external tools (APIs, search engines, databases). This pattern — giving an LLM access to real-world actions — is the defining feature of agents. It transforms LLMs from "text in, text out" to "question in, action in the world, result observed."

The key design decisions:
- Tools should never raise exceptions (use ToolResult.failure pattern)
- Tools should return structured sources, not just raw text
- Credibility scores should be assigned at the source level

### 15.3 Hierarchical Planning

The planner generates a complete plan before execution begins. This is called **plan-then-execute** as opposed to **step-by-step** (where the agent decides the next action after seeing the result of the current one).

**Plan-then-execute advantages:**
- Parallelism is possible (all parallel-ready nodes are known upfront)
- The plan can be validated for cycles before execution
- The plan can be cached or inspected

**Plan-then-execute disadvantages:**
- The plan may become invalid if early tasks return unexpected results
- Less reactive to discoveries mid-execution

Singularity mitigates the disadvantages with replanning: after each round, the planner can issue a new plan based on what was discovered.

### 15.4 Reflection and Self-Correction

The gap analysis → replan loop is a form of **agent reflection**: the system examines its own outputs, identifies deficiencies, and generates a corrective plan. This is a key capability that separates basic tool-using agents from more capable autonomous systems.

The `detect_replan_loop` mechanism is the termination condition for this reflection — without it, the agent could reflect indefinitely without making progress.

### 15.5 Memory and State Accumulation

`ExecutionContext` is the agent's working memory. As nodes execute, results accumulate there. Later nodes can access everything earlier nodes produced. This is how knowledge compounds across the pipeline:

```
retrieval → verified facts → synthesized analysis → final report
```

Each stage has access to all prior stages' outputs via the context.

### 15.6 Structured Output from LLMs

Every LLM call in this system produces JSON, not free text. This is essential for agentic systems because:
- Downstream code needs to read specific fields (confidence, findings, citations)
- Free text can't be reliably parsed programmatically
- JSON lets you validate output with Pydantic

The `_extract_json()` parser handles the two most common patterns: JSON in code fences, and JSON at the start of the response.

### 15.7 Graceful Degradation

The system is designed to produce **some** output even when parts fail:

- `PARTIAL` status means "incomplete but not worthless"
- The FallbackRouter tries alternatives before giving up
- The final report discloses coverage gaps explicitly
- The credibility score reflects actual source quality

This is important for production systems: returning a 70%-complete report with disclosed gaps is more useful than returning nothing because 2 nodes failed.

### 15.8 Context Window Management

The `ContextBudgetManager` solves the context stuffing problem. As pipeline outputs accumulate, naively concatenating everything would exceed token limits and degrade LLM performance. The budget manager:

- Prioritizes direct dependencies (the LLM needs these most)
- Summarizes indirect context (background awareness, not full detail)
- Drops lowest-credibility sources when over budget
- Enforces hard caps per category

This is the key to making 15-node pipelines work without hitting context limits.

---

## 16. What We Learned — Lessons for Agentic AI Design

### 16.1 Explicit State Transitions Beat Implicit Side Effects

The `prior_hashes` bug happened because a state update (`prior_hashes.add()`) was hidden inside a general-purpose method (`ctx.record()`). The state update had a single intended use (loop detection), but it ran in a context (normal execution) where it had unintended consequences.

**Lesson:** In agents, shared mutable state is dangerous. Make state updates explicit and purpose-specific. Methods that have side effects beyond their obvious purpose should be viewed with suspicion.

### 16.2 Interface Contracts Must Be Explicit

The FallbackRouter / BaseRetrievalSkill mismatch happened because two components made different assumptions about how failures are communicated. One expected exceptions; the other used return values.

**Lesson:** Every interface between components should explicitly document: what constitutes success, what constitutes failure, and how failure is signaled. In Python, this means using typed return values, documented exceptions, or explicit error types — not leaving it to convention.

### 16.3 LLMs Plan Well When Given Structured Guidance

The 534-line planner system prompt is long, but it works because it gives the LLM a structured process (six phases), specific constraints (use only registered skills, follow acceptance criteria), and clear output format (JSON DAG + rubric summary).

**Lesson:** LLMs are better planners when you give them a framework to reason within. Telling them "generate a plan" produces worse results than walking them through explicit reasoning steps. This is the core insight behind chain-of-thought and structured prompting techniques.

### 16.4 Separation Between "What to Do" and "How to Do It"

The planner decides *what* tasks to run. The skills know *how* to do each task. The executor decides *when* to run them. The context stores *what was learned*.

This separation of concerns is what makes the system extensible:
- Add a new domain → update `domain_registry.json`
- Add a new skill → implement `BaseRetrievalSkill` or `BaseAnalysisSkill`
- Add a new tool → implement `ToolBase`
- Change the LLM → implement `BaseLLMClient`

None of these changes require touching the other layers.

### 16.5 Data Provenance Matters

Every source has a `citation_id` assigned at retrieval time. This ID follows the source through verification, synthesis, and the final report. You can always trace a claim back to its source.

**Lesson:** In research agents, provenance is not optional. Without knowing where each claim came from, you can't verify the report, assess confidence, or update it when sources become outdated. Build provenance tracking in from the beginning, not as an afterthought.

### 16.6 The Confidence Threshold Is a Policy Decision

The system uses `confidence >= 0.70` as the threshold for `NodeStatus.OK`. This is a policy choice, not a technical constraint. Setting it lower (0.50) would produce more OK nodes but lower quality. Setting it higher (0.85) would produce more PARTIAL nodes, triggering more replanning.

**Lesson:** Quality thresholds in agent systems are business decisions disguised as technical constants. They encode the tradeoff between confidence and completeness. Make them explicit and tunable rather than hardcoded.

### 16.7 Agents Need Termination Conditions at Every Level

Singularity has termination conditions at three levels:
1. **Node level**: `min_ok` sources required; LLM confidence threshold
2. **Round level**: `check_termination()` verifies all nodes are OK
3. **System level**: `detect_replan_loop()` prevents infinite replanning

**Lesson:** Agents that can plan and replan need explicit stopping criteria at every level of recursion. Without them, they will retry forever, burning compute and money without converging.

### 16.8 Async-First Is the Right Default

The entire pipeline uses `asyncio`. The benefit is real: in Wave 0, all 6 retrieval nodes run simultaneously. A synchronous pipeline would run them one after another — 6x the latency. For deep research queries, async parallelism is the difference between a 2-minute run and a 12-minute run.

**Lesson:** If your agent makes multiple independent API calls (which almost all do), async execution is essential for performance. Use `asyncio.gather()` for parallel branches and `asyncio.to_thread()` for sync third-party libraries.

---

## Appendix: File Reference

| File | Lines | Key Exports |
|---|---|---|
| `agents/orchestrator/cli.py` | ~140 | `_legacy_run()`, `_strength_run()` |
| `agents/orchestrator/runner.py` | ~239 | `run_orchestrator()`, `run_gap_analysis()`, `detect_replan_loop()` |
| `agents/orchestrator/pipeline.py` | ~293 | `run_pipeline()`, `_format_report()`, `_phase_c()` |
| `agents/orchestrator/executor.py` | ~41 | `execute_node()`, `execute_wave()` |
| `agents/orchestrator/fallback_router.py` | ~59 | `FallbackRouter` |
| `agents/orchestrator/strength.py` | ~106 | `StrengthConfig` |
| `agents/orchestrator/config.py` | ~47 | All constants |
| `agents/planner/planner.py` | ~206 | `Planner`, `parse_plan()` |
| `agents/planner/domain_registry.py` | ~50 | `DomainRegistry` |
| `agents/retriever/retriever.py` | ~119 | `Retriever`, `run_fanout()` |
| `agents/report_manager/agent.py` | ~70 | `ReportManagerAgent` |
| `agents/report_manager/report_tree.py` | ~157 | `ReportTree`, `topological_levels()` |
| `agents/report_manager/section_node.py` | ~25 | `SectionNode` (content, citations, source_map) |
| `agents/report_lead/agent.py` | ~74 | `ReportLeadAgent` |
| `agents/report_worker/agent.py` | ~215 | `ReportWorkerAgent`, `_make_citation_id()`, `_format_chunks()` |
| `agents/report_worker/result.py` | ~25 | `WorkerResult` (includes source_map) |
| `models.py` | ~477 | All data models (unified) |
| `SKILLS/tier1_retrieval/_base.py` | ~120 | `BaseRetrievalSkill`, `_to_query()` |
| `SKILLS/tier2_analysis/_base.py` | ~120 | `BaseAnalysisSkill`, `_extract_json()` |
| `SKILLS/tier3_output/_base.py` | ~115 | `BaseOutputSkill` |
| `vector_store/client.py` | — | `VectorStoreClient` (Qdrant + in-memory) |
| `context/budget.py` | ~80 | `ContextBudgetManager` |
| `citations/registry.py` | ~100 | `CitationRegistry` (legacy DAG mode) |
| `llm/grok.py` | ~80 | `GrokClient` |
| `agents/planner/system_prompt.md` | ~535 | Planner instructions (6-phase, full skill registry) |
| `agents/planner/domain_registry.json` | ~1150 | 11 domain bundles, fallback chains, skill registry |
| `agents/report_worker/prompt_leaf.md` | — | Leaf worker instructions (2-call, citation rules) |
| `agents/report_worker/prompt_parent.md` | — | Parent worker instructions (synthesis, citation rules) |

---

*This report was written from a complete analysis of the Singularity codebase, covering every module, every bug that was hit and fixed, and the agentic AI principles that underlie the design.*
