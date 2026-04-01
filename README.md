# Singularity

Evidence-driven technical documentation for the current codebase implementation.

This README follows `how_to_document_code.md`:
- documents only implemented behavior,
- maps implementation to engineering concepts,
- states design choices with strengths and limitations,
- explains serialized vs parallel flow,
- includes practical usage and cost/scale approximations.

---

## 0) Quick Start

```bash
# Setup
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Primary path (Phase-5)
python -m agents.orchestrator.cli "research question" --strength 5 --audience expert

# Legacy DAG path
python -m agents.orchestrator.cli "research question" --depth standard

# Chat REPL
python -m agents.chat.cli
```

---

## 1) Navigation

- [2) Project Purpose](#2-project-purpose)
- [3) Runtime Interfaces](#3-runtime-interfaces)
- [4) Repository Structure](#4-repository-structure)
- [5) Architecture](#5-architecture)
- [6) Execution Semantics](#6-execution-semantics)
- [7) Core Modules and Concepts](#7-core-modules-and-concepts)
  - [7.1 Agents](#71-agents)
  - [7.2 Skills and Tier Breakdown](#72-skills-and-tier-breakdown)
  - [7.3 Tools](#73-tools)
  - [7.4 CitationRegistry](#74-citationregistry)
  - [7.5 ContextBudgeting](#75-contextbudgeting)
  - [7.6 LLM Clients and Router](#76-llm-clients-and-router)
  - [7.7 Models and Contracts](#77-models-and-contracts)
  - [7.8 Vector Store](#78-vector-store)
- [8) Generalized Process Pipelines](#8-generalized-process-pipelines)
- [9) Scale and Cost Approximation](#9-scale-and-cost-approximation)
- [10) Version Timeline (V1 -> V2)](#10-version-timeline-v1---v2)
- [11) Decision Register](#11-decision-register)
- [12) Practical Command Surface](#12-practical-command-surface)
- [13) Notes](#13-notes)

---

## 2) Project Purpose

Singularity is a research-agent codebase with two active execution paths:

1. **Legacy DAG orchestrator** via `run_orchestrator`
2. **Phase-5 pipeline (primary)** via `run_pipeline`

Current system composition:
- planning agents,
- retrieval + analysis + output skills,
- external data tools,
- LLM reasoning/writing clients,
- Qdrant-backed retrieval context,
- report assembly + polish.

Primary artifact:
- report rendered to `final_report.html` by orchestrator CLI.

---

## 3) Runtime Interfaces

### 3.1 Orchestrator CLI

- **Path**: `agents/orchestrator/cli.py`
- **Purpose**: one-shot research execution and report rendering.

```bash
# Phase-5 product path (primary)
python -m agents.orchestrator.cli "your question" --strength 5 --audience practitioner

# Legacy DAG path
python -m agents.orchestrator.cli "your question" --depth standard

# Optional trace export
python -m agents.orchestrator.cli "your question" --strength 7 --trace
```

### 3.2 Chat REPL

- **Path**: `agents/chat/cli.py`
- **Purpose**: interactive dual-mode session (`chat` / `research`).

```bash
python -m agents.chat.cli
python -m agents.chat.cli --extended
python -m agents.chat.cli --model grok-3
```

Implemented in-session commands:
- `/model`, `/mode`, `/extended`, `/clear`, `/history`, `/skills`, `/quit`

---

## 4) Repository Structure

```text
agents/
  chat/                # Thinker + chat-mode executor + REPL
  orchestrator/        # CLI, legacy runner, phase-5 pipeline, config, strength
  planner/             # Domain registry and planner assets
  report_manager/      # 3 manager proposal generation
  report_lead/         # proposal synthesis to final tree
  report_worker/       # section writing
  retriever/           # phase-A retrieval planner and fanout
  source_gate/         # source filtering
  polish.py            # report polishing

skills/
  base.py
  registry.py
  skill_docs.py        # skill.md integration layer
  tier1_retrieval/     # 18 retrieval skills
  tier2_analysis/      # 18 analysis skills
  tier3_output/        # 8 output skills

tools/                 # external data connectors
vector_store/          # Qdrant wrapper + embedding pipeline
llm/                   # provider clients + router
models/                # pydantic/dataclass model package
context/               # context budgeting
citations/             # citation registry
render/                # HTML renderer
trace/                 # trace logging
```

---

## 5) Architecture

### 5.1 Path A: Phase-5 Pipeline (primary)

- **Entry**: `agents/orchestrator/pipeline.py:run_pipeline`
- **Order**:
  1. **Phase B** planning (3 managers in parallel + 1 lead synthesis),
  2. **Phase A** retrieval (tree-informed fanout + ingestion),
  3. **Phase C** writing (bottom-up by tree depth),
  4. **Phase D** polish (deterministic cleanup + LLM formatting).

### 5.2 Path B: Legacy DAG Orchestrator

- **Entry**: `agents/orchestrator/runner.py:run_orchestrator`
- **Loop**: plan DAG -> execute waves -> gap analysis -> optional replan loop.

---

## 6) Execution Semantics

### 6.1 Serialized segments

- `run_pipeline` phase boundaries are serialized: **B -> A -> C -> D**.
- Lead synthesis happens after all manager proposals.
- Phase C executes one depth level at a time (bottom-up).

### 6.2 Parallelized segments

- Phase B managers run with `asyncio.gather`.
- Phase A retrieval skills execute in parallel.
- Nodes in the same Phase C depth execute in parallel.
- Polisher runs section-level transformations in parallel.

### 6.3 Why this split

- **Serialization** at dependency boundaries gives deterministic progression.
- **Parallelization** on independent units reduces wall-clock latency.

---

## 7) Core Modules and Concepts

Method used in each subsection:
- what, why, concept family, chosen concept, why chosen, relevance, trade-offs.

### 7.1 Agents

- **What**: role-specialized orchestrators (`planner`, `retriever`, `manager`, `lead`, `worker`, `polisher`, `chat`).
- **Why**: separate planning, retrieval, synthesis, and interaction concerns.
- **Concept Family**: multi-agent orchestration / role decomposition.
- **Chosen Concept**: hybrid architecture (phase-specialized path + retained legacy DAG path).
- **Why Chosen**: preserve compatibility while advancing production flow.
- **Relevance**: `run_pipeline` is explicit phase orchestration; `run_orchestrator` remains available.
- **Trade-offs**:
  - Positive: cleaner phase-level tuning.
  - Negative: more prompts and coordination surfaces.

### 7.2 Skills and Tier Breakdown

- **What**: plugin layer with 44 concrete skills.
  - Tier 1 Retrieval: 18
  - Tier 2 Analysis: 18
  - Tier 3 Output: 8
- **Why**: modular composition of fetch -> reason -> render.
- **Concept Family**: plugin registry + dynamic discovery + tiered processing.
- **Chosen Concept**:
  - `SkillBase.__init_subclass__` for class registration,
  - `skills/registry.py` for instance registry and tier-1 derivation.
- **Why Chosen**: avoids manual centralized skill list edits.
- **Relevance**: planning/execution resolve through `SKILL_REGISTRY`; phase-A constrained by `TIER1_SKILLS`.
- **Trade-offs**:
  - Positive: additive extensibility.
  - Negative: import-side-effect sensitivity.

#### 7.2.1 Tier-1 retrieval skills (18)

`academic_search`, `book_search`, `clinical_search`, `code_search`, `data_extraction`, `dataset_search`, `financial_search`, `forum_search`, `gov_search`, `legal_search`, `multimedia_search`, `news_archive`, `patent_search`, `pdf_deep_extract`, `social_search`, `standards_search`, `video_search`, `web_search`

#### 7.2.2 Tier-2 analysis skills (18)

`causal_analysis`, `citation_graph`, `claim_verification`, `comparative_analysis`, `contradiction_detect`, `credibility_score`, `entity_extraction`, `fallback_router`, `gap_analysis`, `hypothesis_gen`, `meta_analysis`, `quality_check`, `sentiment_cluster`, `statistical_analysis`, `synthesis`, `timeline_construct`, `translation`, `trend_analysis`

#### 7.2.3 Tier-3 output skills (8)

`annotation_gen`, `bibliography_gen`, `decision_matrix`, `exec_summary`, `explainer`, `knowledge_delta`, `report_generator`, `visualization_spec`

### 7.3 Tools

- **What**: external adapters under `tools/`: `arxiv_api`, `clinicaltrials`, `courtlistener`, `dataset_hub`, `github_api`, `google_books`, `pdf_reader`, `pubmed_api`, `sec_edgar`, `semantic_scholar`, `standards_fetch`, `translation`, `web_fetch`, `youtube_transcript`.
- **Why**: isolate provider/API concerns from skill orchestration.
- **Concept Family**: adapter layer with shared return contract.
- **Chosen Concept**: standardized tool wrappers consumed by tier-1 skills.
- **Why Chosen**: consistent metadata and failure handling surface.
- **Relevance**: source ingestion path into Qdrant and report evidence.
- **Trade-offs**:
  - Positive: unified integration boundary.
  - Negative: each adapter inherits provider fragility.

### 7.4 CitationRegistry

- **What**: `citations/registry.py` in-process source registry + bibliography formatting.
- **Why**: preserve provenance and stable citation IDs.
- **Concept Family**: registry + provenance tracking.
- **Chosen Concept**: runtime citation-id generation with URL dedup support.
- **Why Chosen**: stable source identity across retrieval/analysis/output.
- **Relevance**: references and source lineage in report outputs.
- **Trade-offs**:
  - Positive: traceable source path.
  - Negative: in-memory run scope, not a persistent citation DB.

### 7.5 ContextBudgeting

- **What**: `context/budget.py:ContextBudgetManager` for upstream context assembly.
- **Why**: avoid context overflow while prioritizing direct dependencies.
- **Concept Family**: budgeted context curation.
- **Chosen Concept**: direct vs indirect tiers + total cap + truncation.
- **Why Chosen**: bounded prompt size with dependency awareness.
- **Relevance**: used by analysis/output skills via `ExecutionContext`.
- **Trade-offs**:
  - Positive: predictable upper bound and stable prompt shape.
  - Negative: heuristic slot/dependency matching can be imperfect in edge naming.

### 7.6 LLM Clients and Router

- **What**: provider clients in `llm/` + `llm/router.py:get_llm_client`.
- **Why**: central model-provider abstraction with low coupling.
- **Concept Family**: factory + provider polymorphism.
- **Chosen Concept**:
  - `deepseek-*` -> `DeepSeekClient`
  - `grok-*` -> `GrokClient`
  - fallback -> `GeminiClient`
- **Why Chosen**: minimal branching and explicit convention.
- **Relevance**: chat and orchestration can change model IDs without business-logic rewrites.
- **Trade-offs**:
  - Positive: compact integration point.
  - Negative: model-id naming conventions must remain consistent.

### 7.7 Models and Contracts

- **What**: `models/` package split:
  - enums (`IssueType`, `NodeStatus`),
  - plan (`PlanNode`, `Plan`, metadata),
  - context (`ExecutionContext`),
  - output contracts (`RetrievalOutput`, `AnalysisOutput`, `QualityReport`, `OutputDocument`, ...),
  - chunk/storage (`DocumentChunk`, `CitationRecord`).
- **Why**: typed inter-module contracts.
- **Concept Family**: schema-first interfaces.
- **Chosen Concept**: package split with compatibility re-exports in `models/__init__.py`.
- **Why Chosen**: maintainability gain without breaking legacy imports.
- **Relevance**: primary data boundary across all phases.
- **Trade-offs**:
  - Positive: clearer model ownership and typing.
  - Negative: re-export indirection for backward compatibility.

### 7.8 Vector Store

- **What**: `vector_store/client.py:VectorStoreClient` for collection lifecycle, chunk ingest, search, topic cache, and TTL cleanup.
- **Why**: retrieval-augmented section writing with chunk reuse.
- **Concept Family**: RAG store abstraction + semantic cache.
- **Chosen Concept**:
  - default server mode (`QDRANT_URL`),
  - explicit in-memory mode (`QDRANT_FORCE_IN_MEMORY=1` or constructor),
  - lazy init + connection probe + explicit failure.
- **Why Chosen**: explicit operational behavior in production, controlled fallback in dev.
- **Relevance**: Phase A ingest and Phase C retrieval.
- **Trade-offs**:
  - Positive: clear lifecycle semantics and bounded cleanup.
  - Negative: persistent mode adds infrastructure dependency.

---

## 8) Generalized Process Pipelines

### 8.1 Full report generation (Phase-5 primary)

1. Query classification + planning (managers + lead).
2. Retrieval skill selection + query fanout.
3. Tool fetch -> source gate -> chunking -> Qdrant ingest.
4. Bottom-up section writing from semantic chunk retrieval.
5. Assembly + references + polish.

### 8.2 Legacy DAG execution

1. Planner builds DAG.
2. Executor runs topological waves.
3. Gap analyzer reports unresolved nodes.
4. Optional replan loop.
5. Output assembly.

### 8.3 Chat loop

1. Thinker selects mode (`chat` or `research`) and step plan.
2. Chat mode executes short step plan incrementally.
3. Research mode delegates to `run_pipeline`.

---

## 9) Scale and Cost Approximation

This section is approximation-only and assumption-explicit.

### 9.1 Strength scaling (from `StrengthConfig`)

| Strength | Retrieval Skills | Queries/Skill | Retrieval Calls | Section Range | Expected LLM Calls |
|---|---:|---:|---:|---:|---:|
| 1 | 2 | 4 | 8 | 6-10 | 29 |
| 3 | 5 | 4 | 20 | 18-30 | 77 |
| 5 | 9 | 6 | 54 | 30-50 | 125 |
| 7 | 12 | 8 | 96 | 42-70 | 173 |
| 10 | 18 | 10 | 180 | 60-100 | 325 |

Additional strength-controlled parameters:
- `min_results_per_query`: 5 -> 20
- `min_chunks_per_leaf`: 3 -> 10
- augmentation iterations: 2 -> 4
- max web escalations: 1 -> 3

### 9.2 Approximate spend model

Current config comment rates:
- `grok-3-mini`: $0.25 / 1M input, $0.50 / 1M output
- `grok-3`: $3.00 / 1M input, $15.00 / 1M output

Assumptions for rough planning:
- mini call: 2k input + 600 output tokens
- grok-3 write/lead call: 5k input + 1.2k output tokens
- call mix shifts toward worker calls with larger section counts

Implication:
- total run cost increases roughly with retrieval fanout + section count + augmentation loops; at high strengths, growth is multiplicative across these dimensions.

---

## 10) Version Timeline (V1 -> V2)

### 10.1 V1: Legacy DAG (`run_orchestrator`)

- **Problem Identified**: need multi-step research with retry and replan behavior.
- **Concepts Used**: DAG planning, wave execution, fallback routing, gap analysis.
- **Possible Decisions**:
  - linear chain,
  - static DAG,
  - DAG + replan loop.
- **Final Decision**: DAG + replan loop.
- **Reasoning**: stronger resilience than one-shot/linear execution.
- **Strengths**:
  - robust recovery path,
  - explicit dependency graph.
- **Weaknesses**:
  - increased control-loop complexity.

### 10.2 V2: Phase-5 Pipeline (`run_pipeline`, primary)

- **Problem Identified**: retrieval quality drift when evidence collection is not tied to finalized section structure.
- **Concepts Used**: phase separation, parallel proposal synthesis, tree-informed retrieval, bottom-up writing, deterministic + creative polish.
- **Possible Decisions**:
  - retrieval-first,
  - planning-first with tree-informed retrieval,
  - one-shot end-to-end generation.
- **Final Decision**: planning-first -> retrieval -> writing -> polish.
- **Reasoning**: section-targeted retrieval improves relevance and reduces wasted calls.
- **Strengths**:
  - clearer production flow,
  - stronger section-evidence alignment,
  - explicit cost/quality dial.
- **Weaknesses**:
  - more LLM calls,
  - broader orchestration surface.

---

## 11) Decision Register

### 11.1 Skill documentation integration (`skill.md`)

- **Hypothesis**: planner/thinker quality improves when skill selection context is generated from `skill.md` instead of hardcoded summaries.
- **Support**: `skills/skill_docs.py` parses all `skill.md` files and feeds:
  - compact `USE/NOT` menu to thinker,
  - full skill contracts to report managers.
- **Limitations**: markdown parsing remains heuristic and depends on content consistency.
- **Strengths**: documentation-as-source-of-truth, lower drift.
- **Decision Reasoning**: reduces manual menu maintenance and keeps prompts aligned with authored skill docs.

### 11.2 Dynamic skill registration trigger

- **Hypothesis**: `__init_subclass__` + tier imports reduce registration boilerplate.
- **Support**: `skills/base.py` and `skills/registry.py` auto-register and instantiate skill classes.
- **Limitations**: import ordering/side effects still matter.
- **Strengths**: no central list edits per skill.
- **Decision Reasoning**: maintainability gain at current scale outweighs import-side complexity.

### 11.3 Qdrant connection policy

- **Hypothesis**: silent in-memory fallback masks production misconfiguration.
- **Support**: current vector client raises explicit connection errors unless in-memory mode is explicitly requested.
- **Limitations**: stricter startup behavior requires environment discipline.
- **Strengths**: clearer operational failure modes.
- **Decision Reasoning**: explicit failure is preferred over hidden degraded persistence.

---

## 12) Practical Command Surface

### 12.1 Environment setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 12.2 Phase-5 pipeline

```bash
python -m agents.orchestrator.cli "research question" --strength 5 --audience expert
```

### 12.3 Legacy DAG

```bash
python -m agents.orchestrator.cli "research question" --depth standard
```

### 12.4 Chat REPL

```bash
python -m agents.chat.cli
python -m agents.chat.cli --extended
python -m agents.chat.cli --model grok-3
```

### 12.5 Trace export

```bash
python -m agents.orchestrator.cli "research question" --strength 7 --trace
```

---

## 13) Notes

- `ARCHITECTURE.md` remains the deeper companion reference.
- This README intentionally avoids future-state claims and documents implemented behavior only.
