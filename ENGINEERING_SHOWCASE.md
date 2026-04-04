# Singularity — Engineering Showcase

> AI-powered deep-research platform. Multi-agent LLM pipeline plans, retrieves, writes, and polishes fully-cited research reports. Full-stack web application with real-time streaming, BYOK LLM keys, per-report Q&A chat, and production deployment on a $25/month AWS VM.

---

## The Build

| Metric | Number |
|--------|--------|
| Total source lines of code | ~19,000 (Python + TypeScript) |
| Python backend | 18,996 lines across 207 files |
| TypeScript frontend | 6,469 lines across 42 files |
| Development duration | **13 days** (Mar 22 – Apr 3, 2026) |
| Commits | 65 |
| Sole contributor | Nishant Sharma |

### Backend LOC by Module

| Module | Lines | Purpose |
|--------|-------|---------|
| `agents/` | 5,455 | Multi-agent orchestration, planning, retrieval, writing, polish |
| `api/` | 3,738 | FastAPI REST server, auth, middleware, SSE streaming |
| `skills/` | 1,775 | 44 pluggable skills across 3 tiers |
| `render/` | 999 | Self-contained HTML report renderer (KaTeX + Marked.js) |
| `tools/` | 1,386 | 14 external data connector adapters |
| `workers/` | 932 | ARQ background job workers with orphan recovery |
| `db/` | 770 | SQLAlchemy async ORM models + Alembic migrations |
| `vector_store/` | 528 | Qdrant wrapper with fastembed embeddings |
| `models/` | 518 | Pydantic/dataclass contracts |
| `llm/` | 375 | Multi-provider LLM abstraction (Grok, Gemini, DeepSeek) |
| `patch/` | 341 | Report patch/edit service |
| `trace/` | 337 | Execution trace logger |
| `citations/` | 191 | Source provenance and bibliography formatting |
| `storage/` | 175 | Blob storage abstraction (local + S3) |
| `utils/` | 126 | JSON parser utilities |
| `context/` | 102 | Context budget manager for bounded prompts |

---

## Architecture

### Phase-5 Research Pipeline

The core insight: **planning runs before retrieval** so every query targets a real planned section, not a vague topic.

```
Phase B — Planning    :  3 Manager agents propose report trees in parallel → Lead synthesizes
Phase A — Retrieval   :  Tree-informed skill selection → targeted query fanout → source gate → Qdrant
Phase C — Writing     :  Workers write sections bottom-up with evidence augmentation + faithfulness checks
Phase D — Polish      :  Deterministic cleanup + LLM creative formatting
```

Phase letters are intentionally out of alphabetical order (B→A→C→D) to reflect the architectural decision that planning (B) must precede retrieval (A).

### Full-Stack Data Flow

```
Browser (Next.js 16 + React 19)
  ├── Google OAuth → FastAPI /api/v1/auth/google
  ├── Dashboard → POST /api/v1/research/jobs (submit research)
  ├── SSE stream → GET /api/v1/research/jobs/{id}/events (real-time progress)
  ├── Report viewer → GET /api/v1/reports/{id}/versions/{v}
  ├── Report edit → POST /api/v1/reports/{id}/versions/{v}/patch
  └── Chat → POST /api/v1/threads/{id}/messages
       │
       └──→ FastAPI (uvicorn)
              ├── Middleware: RequestID → Auth → RateLimit → UsageEmitter → CORS
              ├── ARQ Redis: enqueue_job → Worker process
              │     ├── run_research_job → run_pipeline() → ReportVersion
              │     ├── run_summary_job → thread summarization
              │     └── run_patch_job → report edits
              ├── PostgreSQL 16: 8 tables, 12 indexes, 5 migrations
              ├── Qdrant: per-run vector collections for RAG retrieval
              └── Blob Storage: local filesystem or S3
```

### LLM Architecture — Pure BYOK

**Every single LLM call in the entire pipeline uses the user's own model + their own API key.** The platform never pays for inference.

How it works (`workers/research_job.py`):

1. User selects a model from the dashboard
2. Worker resolves their stored BYOK key for that model's provider
3. One `_pipeline_llm_client(model_id, llm_api_key)` is created
4. That single client is passed to every agent — planner, managers, lead, workers, retriever, source gate, polisher

The `config.py` model constants are legacy — only used by the old CLI/DAG orchestrator path. The production Phase 5 pipeline creates one client from the user's chosen model and routes every call through it.

**10 models available** across 3 providers:

| Provider | Models | Notes |
|----------|--------|-------|
| **xAI Grok** | grok-3, grok-3-mini, grok-3-mini-fast | Flagship + fast variants |
| **Google Gemini** | gemini-2.5-pro-preview-03-25, gemini-2.5-flash-preview-04-17, gemini-2.0-flash, gemini-2.0-flash-thinking-exp | Pro, Flash, and Thinking variants |
| **DeepSeek** | deepseek-chat (V3), deepseek-reasoner (R1) | Standard + chain-of-thought |

BYOK keys are **Fernet-encrypted at rest** in PostgreSQL, decrypted only at job runtime. One key per user per provider.

### 3 Intensity Tiers

The `StrengthConfig` class scales 14 independent parameters based on 3 user-selectable intensity levels:

| Parameter | Low (1) | Medium (2) | High (3) |
|-----------|---------|------------|----------|
| Internal scale (legacy) | 3 | 6 | 10 |
| Retrieval skills activated | 5 | 10 | 18 |
| Queries per skill | 4 | 6 | 10 |
| Section count range | 18–30 | 36–60 | 60–100 |
| Augmentation iterations (per leaf) | 2 | 2 | 4 |
| Web escalations (per leaf) | 1 | 1 | 3 |
| Min results per query | 6 | 12 | 20 |
| Expected LLM calls | ~21 | ~77 | ~130+ |

---

## Skills System — 44 Pluggable Skills

Auto-registered via `__init_subclass__` metaclass. Zero manual wiring. Each skill is a self-contained directory with its own module + markdown doc.

### Tier 1 — Retrieval (18 skills)

| Skill | Data Source |
|-------|------------|
| `web_search` | DuckDuckGo + Tavily |
| `academic_search` | Semantic Scholar, ArXiv |
| `pdf_deep_extract` | Direct PDF parsing (pdfplumber + PyMuPDF) |
| `video_search` | YouTube transcript extraction |
| `code_search` | GitHub API |
| `dataset_search` | HuggingFace Hub |
| `clinical_search` | ClinicalTrials.gov |
| `legal_search` | CourtListener |
| `financial_search` | SEC EDGAR filings |
| `patent_search` | Patent databases |
| `gov_search` | Government portals |
| `news_archive` | News archive search |
| `book_search` | Google Books API |
| `social_search` | Social media sources |
| `forum_search` | Forum/thread search |
| `standards_search` | Standards bodies (ISO, IEEE, etc.) |
| `multimedia_search` | Multimedia content |
| `data_extraction` | Structured data extraction |

### Tier 2 — Analysis (18 skills)

`causal_analysis`, `citation_graph`, `claim_verification`, `comparative_analysis`, `contradiction_detect`, `credibility_score`, `entity_extraction`, `fallback_router`, `gap_analysis`, `hypothesis_gen`, `meta_analysis`, `quality_check`, `sentiment_cluster`, `statistical_analysis`, `synthesis`, `timeline_construct`, `translation`, `trend_analysis`

### Tier 3 — Output (8 skills)

`annotation_gen`, `bibliography_gen`, `decision_matrix`, `exec_summary`, `explainer`, `knowledge_delta`, `report_generator`, `visualization_spec`

---

## 14 External Data Connectors

Each tool is an isolated adapter behind a base class, with per-attempt timeout protection:

| Connector | Source |
|-----------|--------|
| `arxiv_api` | ArXiv preprint server |
| `clinicaltrials` | ClinicalTrials.gov |
| `courtlistener` | CourtListener legal database |
| `dataset_hub` | HuggingFace datasets |
| `github_api` | GitHub repositories (PyGithub) |
| `google_books` | Google Books API |
| `pdf_reader` | PDF deep extraction (pdfplumber + PyMuPDF) |
| `pubmed_api` | PubMed/NCBI (biopython) |
| `sec_edgar` | SEC EDGAR financial filings |
| `semantic_scholar` | Semantic Scholar academic search |
| `standards_fetch` | Standards bodies |
| `translation` | Translation service |
| `web_fetch` | Generic web page fetching |
| `youtube_transcript` | YouTube video transcripts |

Coverage spans: academic papers, legal cases, medical trials, financial filings, code repositories, video content, books, datasets, standards documents, and general web.

---

## Vector Store — RAG with Qdrant

| Feature | Detail |
|---------|--------|
| Embedding model | fastembed/all-MiniLM-L6-v2 |
| Dimensions | 384 |
| Runtime | ONNX (no PyTorch, no GPU) |
| Weight savings | 1.4 GB lighter than sentence-transformers |
| Distance metric | Cosine similarity |
| Per-run collections | Isolated Qdrant collection per research run |
| Topic cache | 0.92 similarity threshold, 7-day TTL |
| Batch upsert | 64 points per call |
| Payload indexing | Credibility score filter on Qdrant payloads |
| Thread pool | All blocking ML + Qdrant ops run in thread pool to prevent event loop starvation |
| Cloud option | Qdrant Cloud for production (saves ~42 MB RAM on-instance) |

---

## Backend — FastAPI

### 31 REST + SSE Endpoints across 6 Routers

**Auth** (`/api/v1/auth/`):
- `POST /google` — Google OAuth login
- `POST /refresh` — Refresh token rotation
- `POST /logout` — Revoke refresh token
- `GET /sse-token` — Issue 30-second single-use SSE JWT

**Research** (`/api/v1/research/`):
- `POST /jobs` — Submit research job
- `GET /jobs/{job_id}` — Get job status
- `GET /jobs/{job_id}/events` — SSE stream for real-time progress
- `POST /jobs/{job_id}/cancel` — Cancel a running job

**Reports** (`/api/v1/reports/`):
- `GET /` — List user's reports
- `GET /{report_id}` — Report metadata
- `DELETE /{report_id}` — Delete report
- `GET /{report_id}/versions` — List versions
- `GET /{report_id}/versions/{version_num}` — Get version content
- `POST /{report_id}/versions/{version_num}/patch` — Apply LLM-powered edit
- `GET /{report_id}/versions/{version_num}/export` — Export version
- `GET /{report_id}/threads/default` — Get default Q&A thread

**Threads** (`/api/v1/threads/`):
- `POST /` — Create thread
- `GET /` — List threads
- `GET /{thread_id}` — Get thread with messages
- `PATCH /{thread_id}` — Update thread
- `DELETE /{thread_id}` — Delete thread
- `POST /{thread_id}/messages` — Send message

**Users** (`/api/v1/users/`):
- `GET /me` — User profile
- `GET /me/stats` — Usage statistics
- `GET /me/usage` — Usage time series
- `GET /me/usage/models` — Model breakdown
- `GET /me/usage/devices` — Device breakdown
- `GET /me/llm-credentials` — List BYOK keys
- `PUT /me/llm-credentials/{provider}` — Store/update BYOK key
- `DELETE /me/llm-credentials/{provider}` — Delete BYOK key

**LLM** (`/api/v1/llm/`):
- `GET /models` — List available models

### Middleware Stack

Execution order: `RequestID → Auth → RateLimit → UsageEmitter → CORS`

| Middleware | Purpose |
|------------|---------|
| `RequestIDMiddleware` | UUID per request, `X-Request-ID` header propagated request→response |
| `AuthMiddleware` | JWT validation on all `/api/v1/*` routes (except whitelisted paths) |
| `RateLimitMiddleware` | Redis sorted-set sliding window, 60 req/min per user, fail-open on Redis outage |
| `UsageEmitterMiddleware` | Fire-and-forget `UsageEvent` record per request (async, never blocks response) |
| `CORSMiddleware` | Dev: regex-matched localhost; Prod: explicit origin list |

### Auth & Security

| Feature | Implementation |
|---------|---------------|
| OAuth | Google ID token verification via `google.oauth2.id_token` |
| Access tokens | JWT, 15-minute expiry, HS256, `type=access` claim enforced |
| Refresh tokens | Opaque, SHA-256 hashed at rest, 30-day expiry |
| Token rotation | Family-based rotation with **reuse detection** — reused token revokes entire family, forces re-auth |
| SSE auth | Separate 30-second single-use JWT (`type=sse`) — prevents long-lived token in query params |
| BYOK key storage | Fernet-encrypted at rest in PostgreSQL, decrypted only at job runtime |
| Non-root Docker | Production API container runs as non-root user |
| Security headers | Caddy sets `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `X-XSS-Protection: 1`, `Referrer-Policy: strict-origin-when-cross-origin` |
| SSL | Caddy auto-provisions Let's Encrypt certificates |
| Docs disabled in prod | `/docs` and `/redoc` only served when `ENVIRONMENT=development` |

---

## Database — PostgreSQL 16

### 8 Tables, 12 Indexes, 5 Migrations

**Tables** (`db/models.py`, 335 lines):

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `users` | User accounts (Google OAuth) | `google_sub` (unique), `email` (unique), `daily_token_budget`, `is_active` |
| `refresh_tokens` | Refresh token rotation | `token_hash` (SHA-256), `family_id`, `revoked_at` |
| `user_llm_credentials` | BYOK encrypted API keys | `provider`, `encrypted_secret` (Fernet), unique per (user, provider) |
| `reports` | Research reports | `query`, `strength`, `user_id` |
| `report_versions` | Immutable version history | `version_num`, `content_inline`, `content_uri`, `content_hash` (SHA-256), `char_count` |
| `research_jobs` | Background research jobs | `status`, `strength`, `llm_model_id`, `current_phase`, `attempts`, `max_attempts` |
| `threads` | Chat threads per report | `report_id`, `summary`, `canonical_report_qa` |
| `messages` | Chat messages | `role`, `content`, `token_count` |
| `usage_events` | Append-only analytics | `event_type`, `route`, `duration_ms`, `device_type`, `os`, `browser`, `ip_address` |

**Indexes**:

| Index | Table | Columns | Type |
|-------|-------|---------|------|
| `ix_users_google_sub` | users | `google_sub` | B-tree, unique |
| `idx_rt_user_id` | refresh_tokens | `user_id` | B-tree |
| `uq_user_llm_provider` | user_llm_credentials | `user_id, provider` | Unique constraint |
| `idx_user_llm_credentials_user` | user_llm_credentials | `user_id` | B-tree |
| `idx_reports_user_id` | reports | `user_id, created_at` | Compound |
| `uq_report_version` | report_versions | `report_id, version_num` | Unique constraint |
| `idx_rv_report_id` | report_versions | `report_id, version_num` | Compound |
| `idx_rj_idempotency` | research_jobs | `user_id, idempotency_key` | Partial unique (PostgreSQL `WHERE idempotency_key IS NOT NULL`) |
| `idx_rj_user_status` | research_jobs | `user_id, status` | Compound |
| `idx_threads_user_id` | threads | `user_id, created_at` | Compound |
| `idx_messages_thread` | messages | `thread_id, created_at` | Compound |
| `idx_ue_user_day` | usage_events | `user_id, created_at` | Compound |
| `idx_ue_event_type` | usage_events | `user_id, event_type, created_at` | Compound |

**Connection pooling** (`db/session.py`):

| Setting | Value |
|---------|-------|
| `pool_size` | 5 |
| `max_overflow` | 10 (burst up to 15 total) |
| `pool_pre_ping` | True (auto-detect stale connections) |
| `pool_recycle` | 300s (recycle connections every 5 min) |
| Driver | asyncpg (fully async) |
| Session | `async_sessionmaker`, `expire_on_commit=False` |

### PostgreSQL Tuned for 2GB VM

| Parameter | Value | Notes |
|-----------|-------|-------|
| `shared_buffers` | 64 MB | 25% of container's 256 MB cap |
| `effective_cache_size` | 128 MB | |
| `work_mem` | 2 MB | |
| `maintenance_work_mem` | 32 MB | |
| `max_connections` | 50 | |

---

## Worker System — ARQ (Redis Queue)

| Setting | Value |
|---------|-------|
| Max concurrent jobs | 4 global |
| Job timeout | 30 minutes hard cap |
| Max retries | 3 attempts |
| Result retention | 1 hour in Redis |
| Job functions | `run_research_job`, `run_debug_mock_research_job`, `run_patch_job`, `run_summary_job` |

### Job Lifecycle

1. API creates `Report` + `ResearchJob`, enqueues to ARQ
2. Worker picks up job, marks `running`, publishes SSE `job_status` event
3. `run_pipeline()` executes phases B → A → C → D with phase + activity callbacks
4. Each callback publishes SSE events via Redis pub/sub (`job:{id}:events` channel)
5. On success: saves `ReportVersion` (inline if <500 KB, else blob storage), marks `done`
6. On cancel: `CancelToken` checks `expires_at` at every phase callback
7. On failure: increments `attempts`, marks `failed` if exhausted, re-raises for ARQ retry otherwise

### Orphan Recovery

On worker startup, `_recover_orphaned_jobs()` scans for jobs in `running` or `pending` state (left over from a previous crash), marks them `failed`, and publishes `job_error` SSE events so the frontend surfaces the error immediately.

### Idempotency

Job creation supports an `idempotency_key`. If a job with the same key exists within the last 24 hours (enforced by a PostgreSQL partial unique index), the existing job is returned instead of creating a duplicate.

---

## Concurrency & Rate Limiting

| Control | Value | Implementation |
|---------|-------|----------------|
| Max concurrent jobs (global) | 4 | ARQ `max_jobs` |
| Max concurrent jobs per user | 2 | DB query count on `pending`/`running` jobs |
| API rate limit | 60 req/min per user | Redis sorted-set sliding window (ZREMBYRANGE + ZCARD + ZADD in atomic pipeline) |
| Daily token budget per user | 1,000,000 tokens | Sum of `UsageEvent.prompt_tokens + completion_tokens` for today |
| Job expiry | 35 minutes from creation | `CancelToken` checks at every phase callback |
| Rate limit fail-open | Yes | If Redis is unreachable, requests pass through with logged warning |

---

## Redis Layer

| Setting | Value |
|---------|-------|
| Image | `redis:7-alpine` |
| Memory cap | 128 MB container, 96 MB Redis `maxmemory` |
| Eviction policy | `allkeys-lru` — self-cleaning under pressure |
| Persistence | AOF (`appendonly yes`) + RDB snapshots (`save 60 1000`) |
| Role | Job queue (ARQ) + SSE pub/sub channels + rate limiting sorted sets |

Rate limiting uses a **real sliding window** (not a fixed counter): `ZREMBYRANGE` trims old entries, `ZCARD` counts the current window, `ZADD` adds the new request — all in a single Redis pipeline transaction. TTL auto-cleans the key.

---

## Real-Time Streaming Architecture

```
Worker (Python) → Redis pub/sub → FastAPI SSE endpoint → Browser EventSource
```

- Per-job Redis channel: `job:{job_id}:events`
- Two event types: `job_status` (phase transitions) + `job_activity` (granular progress)
- Frontend `ResearchOperationsFeed` renders a real-time storyboard
- Activity events: `pipeline_start`, `domain_classified`, `managers_spawn`, `retrieval_plan_ready`, `retrieval_skill_finished`, `writers_depth`, `polish_started`, `polish_finished`
- 10-minute warning shown on frontend when job runs long

---

## Frontend — Next.js 16 + React 19

| Page | File | Lines | Purpose |
|------|------|-------|---------|
| Landing | `src/app/page.tsx` | — | Product landing page |
| Dashboard | `src/app/dashboard/page.tsx` | 764 | Research submission + job history |
| Report Viewer | `src/app/reports/[id]/page.tsx` | 889 | Report display + TOC + patch modal |
| Profile | `src/app/profile/page.tsx` | — | BYOK key management + usage stats |

### Key Components (19 total)

| Component | Purpose |
|-----------|---------|
| `ChatPanel` (703 lines) | Full chat interface with streaming responses |
| `ReportViewer` | Markdown rendering with KaTeX math + GFM tables |
| `ReportTOC` | Table of contents sidebar |
| `ResearchOperationsFeed` | Real-time activity feed during research |
| `PatchModal` | Report editing via LLM patches |
| `SelectionToolbar` | Text selection actions |
| `ChatModelPicker` | Model selection for chat |
| `MessageBubble` | Chat message rendering |
| `StreamingMessage` | Streaming chat message display |
| `chat_history_sidebar` | Chat thread navigation |
| `profile_llm_keys_section` | BYOK key management UI |

### Frontend Libraries

| Category | Libraries |
|----------|-----------|
| Framework | Next.js 16, React 19 |
| Auth | NextAuth v5 (beta) |
| State | Zustand |
| Data fetching | TanStack React Query |
| UI primitives | Radix UI |
| Charts | Recharts |
| Animation | Framer Motion |
| Math rendering | KaTeX |
| Markdown | react-markdown, remark-gfm, remark-math, rehype-katex |
| Styling | Tailwind CSS 4 |
| Icons | Lucide React |
| Toasts | Sonner |

### Frontend Lib Layer (12 modules)

| Module | Purpose |
|--------|---------|
| `api.ts` | API client (10 KB) |
| `sse.ts` | Server-Sent Events client |
| `research_activity_presenter.ts` | Activity feed data transformation |
| `normalize_math_markdown.ts` | Math markdown normalization |
| `normalize_gfm_pipe_tables.ts` | GFM table normalization |
| `normalize_chat_assistant_markdown.ts` | Chat markdown normalization |
| `llm_model_groups.ts` | Model grouping for UI |
| `byok_recommended_models.ts` | BYOK model recommendations |
| `public_api_base_url.ts` | Public API URL resolution |
| `debug_research_mock.ts` | Debug mock research mode |
| `cn.ts` | Class name utility |
| `utils.ts` | General utilities |

---

## Observability

| Layer | What's Tracked |
|-------|---------------|
| **Request tracing** | `X-Request-ID` on every request/response, propagated through all middleware |
| **Usage analytics** | `UsageEvent` table — append-only records: event_type, route, duration_ms, success, status_code, user_agent, IP, device_type, OS, browser, session_id |
| **Phase tracking** | `ResearchJob.current_phase` column updated in DB at each phase transition + SSE event |
| **Activity feed** | `job_activity` SSE events for pipeline lifecycle milestones |
| **Sentry** | Optional — FastAPI + SQLAlchemy integrations, 20% trace sample rate |
| **Execution trace** | `TraceLogger` module — structured debug logging for full pipeline observability |
| **Job timing** | `created_at`, `started_at`, `finished_at`, `expires_at` — full lifecycle columns |

---

## Resilience & Fault Tolerance

| Scenario | Behavior |
|----------|----------|
| Worker crash mid-job | On restart, orphan recovery scans for `running` + `pending` jobs, marks them failed, publishes SSE error |
| Job timeout | `CancelToken` checks `expires_at` at every phase callback, raises `asyncio.CancelledError` |
| LLM 429 rate limit | Caught at job creation, returns 429 with actionable message |
| Tool/adapter hang | Per-attempt timeout on all 14 data connector tools |
| Redis down | Rate limiter fails open (passes through, logs warning); healthcheck catches it |
| PostgreSQL down | Healthcheck `/api/ready` catches it; connection pool `pre_ping` auto-recovers |
| OOM | Every Docker container has hard memory cap; worker gets 1 GB headroom |
| Large reports | Inline storage if <500 KB, automatic S3/blob offload if larger |
| Duplicate job submission | Idempotency key with PostgreSQL partial unique index (24-hour window) |

---

## Storage

| Mode | Trigger | Storage |
|------|---------|---------|
| Inline | Report < 500 KB | `content_inline` column in `report_versions` table |
| Blob overflow | Report >= 500 KB | S3, Cloudflare R2, MinIO, or local filesystem |
| Content integrity | Always | SHA-256 hash stored in `content_hash` column |
| Versioning | Always | Append-only `ReportVersion` rows with monotonically increasing `version_num` |

---

## Domain Intelligence

- **11 domain categories** with per-domain retrieval strategies: ML Research, Legal, Medical/Clinical, Journalism, Market Research, Policy Analysis, Engineering Standards, Historical/Humanities, Product/UX, Finance/Investment, General
- **110 sub-domain entries** with specialized source recommendations
- **5 audience output rules** — adjusts report style based on intended audience
- **2-pass source gate** — credibility filtering before and after retrieval

---

## Other Engineering Details

| Component | Detail |
|-----------|--------|
| **ContextBudgetManager** | Bounded prompt assembly: direct deps get 3,000 tokens, indirect get 350 chars, hard 32K char total cap, credibility-ordered truncation |
| **CitationRegistry** | Full provenance tracking from source → chunk → report section → bibliography |
| **HTML Report Renderer** | 996-line self-contained HTML generator with embedded KaTeX + Marked.js, light theme, LaTeX math, GFM tables |
| **Report Patch System** | Slug generation, validation, atomic edit application via LLM |
| **Blob Storage Abstraction** | `LocalStorage` and `S3BlobStore` behind common interface, configurable via `BLOB_STORE` env var |
| **Structured JSON extraction** | Robust parser for extracting JSON from LLM output with markdown fences, extra prose, or malformed quotes |
| **Junk URL filter** | Frozenset of 9 known junk/redirector domains filtered from reference lists |

---

## Production Deployment

### AWS t3-small (2 GB RAM) — ~$25/month

| Service | Image | Memory Cap | Notes |
|---------|-------|------------|-------|
| Caddy | `caddy:2-alpine` | 64 MB | Reverse proxy + auto-SSL (Let's Encrypt) |
| PostgreSQL 16 | `postgres:16-alpine` | 256 MB | Tuned for low-memory |
| Redis 7 | `redis:7-alpine` | 128 MB | LRU eviction, AOF persistence |
| API Server | Multi-stage Python 3.12-slim | 256 MB | Non-root user in production |
| Background Worker | Same image | 1 GB | ML + LLM call headroom |
| Next.js Frontend | Standalone build | 128 MB | Pre-built on Docker Hub |

**Total committed: ~1.8 GB** on a 2 GB box.

### Docker Strategy

- Multi-stage builds for both API and frontend
- Production images pre-built and pulled from Docker Hub (`hellonish/singularity-api`, `hellonish/singularity-frontend`)
- `docker-compose.prod.yml` — pull-only, no on-server builds
- `docker-compose.test.yml` — simulates t3-small memory constraints locally
- Every container has healthchecks
- Qdrant offloaded to Qdrant Cloud (saves ~42 MB on-instance)

### CI/CD — GitHub Actions

Pipeline runs on every push/PR:
- Ubuntu runner with PostgreSQL 16 + Redis 7 service containers
- Python 3.12, pip install, Alembic migrations against real PostgreSQL, pytest
- Qdrant in `FORCE_IN_MEMORY=1` mode for tests
- 19 test files across skills and tool integration tests

---

## The Cost Model

The platform **never pays for LLM inference**. Every call uses the user's BYOK key. Infrastructure cost is fixed:

| Resource | Monthly Cost |
|----------|-------------|
| AWS t3-small (2 GB) | ~$25 |
| Qdrant Cloud (free tier) | $0 |
| Domain + SSL (Caddy / Let's Encrypt) | ~$1 |
| **Total** | **~$26/month** |

Fixed-cost, zero-marginal-cost-per-user model for compute. Variable costs limited to Postgres storage growth (reports, usage events), bounded by the daily token quota per user.

---

## Development Journey

| Phase | Date | Milestone |
|-------|------|-----------|
| Foundation | Mar 22 | Base deep research agent with DAG orchestrator |
| Skills + Tools | Mar 25 | 44 skills, 14 tools, planner, LLM routing |
| Orchestration v2 | Mar 26 | Phase-5 pipeline (planning before retrieval), HTML renderer |
| Report Quality | Mar 26 | LaTeX math, GFM tables, citation formatting, JSON parsing |
| Web Application | Apr 01–02 | Next.js 16 frontend, FastAPI backend, Google OAuth, SSE streaming |
| Production Hardening | Apr 03 | Docker optimization, AWS t3-small deployment, healthchecks |
| Worker Resilience | Apr 03 | OOM fix, orphan recovery, rate limit handling, timeout protection |
| Embedding Optimization | Apr 03 | sentence-transformers → fastembed (1.4 GB lighter), Qdrant payload indexing |

---

## Summary Numbers

| | |
|---|---|
| Lines of code | ~19,000 (Python) + ~6,500 (TypeScript) |
| Backend files | 207 Python |
| Frontend files | 42 TypeScript |
| Pluggable skills | 44 (18 retrieval + 18 analysis + 8 output) |
| Data connectors | 14 tools |
| LLM providers | 3 (xAI Grok, Google Gemini, DeepSeek) |
| Available models | 10 |
| API endpoints | 31 |
| Database tables | 8 |
| Database indexes | 12 (including 1 partial unique) |
| Migrations | 5 |
| Middleware layers | 5 (RequestID, Auth, RateLimit, UsageEmitter, CORS) |
| Docker containers | 6 in production |
| Production VM | AWS t3-small, 2 GB RAM, ~$25/month |
| Total prod memory | ~1.8 GB across 6 containers |
| Build time | 13 days, 65 commits, 1 engineer |
