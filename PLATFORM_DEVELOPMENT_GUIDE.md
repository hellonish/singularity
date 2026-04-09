# Singularity Platform — Production Development Guide

> **Last updated:** 2026-04-01
> **Status:** Active — execution in progress

---

## Table of Contents

1. [Current State Assessment](#1-current-state-assessment)
2. [Product Specification (Final)](#2-product-specification-final)
3. [System Design Principles](#3-system-design-principles)
4. [Target Architecture](#4-target-architecture)
5. [Agent Team Structure](#5-agent-team-structure)
6. [Backend Development Plan](#6-backend-development-plan)
7. [Frontend Development Plan](#7-frontend-development-plan)
8. [Usage Tracking System](#8-usage-tracking-system)
9. [Edge Cases and Failure Modes](#9-edge-cases-and-failure-modes)
10. [Infrastructure and Hosting](#10-infrastructure-and-hosting)
11. [How to Spawn the Agent Team in Claude Code](#11-how-to-spawn-the-agent-team-in-claude-code)

---

## 1. Current State Assessment

### Engine (built, do not modify internals)

| Module | Notes |
|--------|-------|
| `agents/orchestrator/pipeline.py` | Phase-5 pipeline: B→A→C→D |
| `agents/chat/agent.py + thinker.py + executor.py` | Dual-mode chat, streaming-capable |
| `skills/` (44 skills, 3 tiers) | Auto-registered, pluggable |
| `tools/` (14 adapters) | Fallback chains, retries |
| `llm/router.py` | Grok, Gemini, DeepSeek routing |
| `vector_store/client.py` | Qdrant with in-memory fallback |
| `citations/registry.py` | Source provenance |
| `context/budget.py` | Token budget management |
| `models/` | Dataclass contracts |

### Nothing built yet

- No web server, no persistence, no auth, no frontend, no job queue, no usage tracking.

### Two integration entry points

```python
# 1. Long-running report generation → goes to background worker
from agents.orchestrator.pipeline import run_pipeline
markdown = await run_pipeline(query, strength, ...)

# 2. Streaming chat (real-time, SSE-suitable)
from agents.chat.agent import ChatAgent
async for chunk in ChatAgent().chat(message, history, active_report_md=...):
    yield chunk
```

---

## 2. Product Specification (Final)

### 2.1 Authentication
- **Google OAuth only** — no email/password. Landing page = Google sign-in.
- Backend verifies Google ID token, issues own JWT pair.
- User row created on first login (upsert by Google `sub` ID).

### 2.2 Dashboard (post-login home)
- **Chat bar at the bottom** — same UX as ChatGPT. User types a research query here.
- **Reports grid above** — shows all projects (reports) user has created. Each report card shows title, date, status.
- Typing in the chat bar and submitting → creates a new research job → redirects to the report once done (with live progress shown inline).
- Chat bar also supports direct Q&A (chat mode) without generating a full report.

### 2.3 Report View (`/reports/[id]`)
- Full rendered markdown report (left/center).
- **Chat panel** (right, slide-in) — follows up with report context + live web access.
- **Text selection → patch flow** — select text in report → "Edit" toolbar appears → instruction modal → LLM patches that section → new version saved.
- Version history accessible via badge.

### 2.4 Dual-Mode Transitions
- **Chat → Report**: If a chat thread gets substantive, user can click "Generate Report from this conversation" → runs pipeline with chat context as seed → creates a new report.
- **Report → Chat**: Chat panel on the report page is always available, inherits full report as context.

### 2.5 Design Language
- **Minimalistic base**: Clean white/off-white light mode, or deep neutral dark mode.
- **Animated personality**: Framer Motion — page transitions, chat bubble entrance, streaming text cursor, report card hover lift, gradient shimmer on loading states.
- **No clutter**: No sidebars full of icons. Content-first layout.
- Monospace or geometric sans-serif font (e.g. Inter or Geist).
- Subtle glassmorphism on cards/panels where appropriate.

### 2.6 Usage Tracking (Backend)
Track every meaningful event for analytics, billing, and debugging:
- What model, how many tokens, cost in USD
- What feature (research_job, chat_qa, patch, etc.)
- What time, device type, OS, browser, country (from IP)
- Success/failure, duration, linked report/job

---

## 3. System Design Principles

| # | Principle |
|---|-----------|
| P1 | **Engine purity** — agents/ has zero HTTP/DB imports. Platform wraps the engine. |
| P2 | **Async-first** — no route handler blocks. Long work = background worker. |
| P3 | **Ownership on every row** — every table has `user_id`. Service layer enforces it. |
| P4 | **Idempotency** — duplicate research jobs within 24h return the same job. |
| P5 | **Optimistic locking** — patches use ETag + `If-Match`. 409 on conflict. |
| P6 | **Costs are first-class** — quota checked before expensive operations. |
| P7 | **Fail loudly at boundaries** — structured JSON errors, no raw tracebacks. |
| P8 | **Usage tracking is non-blocking** — emitted async, never delays the request. |

---

## 4. Target Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                    Next.js 14  (Vercel)                        │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Landing (Google Sign-in)  →  Dashboard (Chat + Reports) │  │
│  │  Report View (Markdown + Chat Panel + Patch toolbar)     │  │
│  └─────────────────────────────┬───────────────────────────┘   │
└────────────────────────────────┼───────────────────────────────┘
                                 │ REST + SSE
┌────────────────────────────────▼───────────────────────────────┐
│                     FastAPI  /api/v1                           │
│  /auth/google   /research/jobs   /reports   /threads           │
│  /users/me/stats   /users/me/usage                             │
├────────────────────────────────────────────────────────────────┤
│  Middleware: JWT auth · Rate limit · Usage emitter              │
└──────────────┬───────────────────────────────┬─────────────────┘
               │ enqueue                        │ read/write
┌──────────────▼──────────────┐   ┌────────────▼────────────────┐
│     ARQ Workers (Redis)     │   │       Data Layer            │
│  run_research_job()         │   │  PostgreSQL (SQLAlchemy 2)  │
│  run_patch_job()            │   │  Redis (queue + cache + SSE)│
│  run_summary_job()          │   │  S3/R2 (markdown blobs)     │
└─────────────────────────────┘   │  Qdrant (vector search)     │
                                  └─────────────────────────────┘
```

---

## 5. Agent Team Structure

### Roles and Responsibilities

```
┌─────────────────────────────────────────────────────────────┐
│                    TECH LEAD (Supervisor)                    │
│  Reviews all PRs. Resolves conflicts. Final arch decisions.  │
│  Unblocks agents. Writes integration tests.                  │
└────────┬──────────┬───────────────┬──────────┬──────────────┘
         │          │               │          │
    ┌────▼───┐ ┌────▼────┐  ┌──────▼───┐ ┌────▼─────┐
    │ BE-1   │ │  BE-2   │  │  BE-3    │ │  FE-1    │
    │ Infra  │ │ Auth +  │  │ Reports  │ │ Auth +   │
    │ Docker │ │ Jobs +  │  │ Patch +  │ │ Dashboard│
    │ CI/CD  │ │ Workers │  │ Usage    │ │ Landing  │
    └────────┘ └─────────┘  └──────────┘ └──────────┘
                                              │
                                         ┌────▼─────┐
                                         │  FE-2    │
                                         │ Report   │
                                         │ View +   │
                                         │ Chat UI  │
                                         └──────────┘
         │
    ┌────▼─────────────────────────────────────────┐
    │                QA / TESTER                   │
    │  Writes pytest + Playwright E2E. Reviews      │
    │  all new endpoints for missing coverage.      │
    └──────────────────────────────────────────────┘
```

### Task Assignment

| Agent | Owns | Deliverables |
|-------|------|-------------|
| **BE-1 (Infra)** | `docker-compose.yml`, `Dockerfile`, `Makefile`, `requirements_api.txt`, `pyproject.toml`, `.env.example`, CI pipeline | Running dev environment |
| **BE-2 (Core API)** | `api/` (incl. `api/db/`), `api/auth/`, `api/research/`, `workers/` | Auth + research jobs + SSE |
| **BE-3 (Features)** | `api/reports/`, `api/threads/`, `patch/`, `api/users/`, usage tracking middleware | Reports, Q&A, patch, stats |
| **FE-1 (Foundation)** | `frontend/` setup, Google Auth, landing page, dashboard shell, design system | Authenticated app shell |
| **FE-2 (Report UI)** | Report viewer, chat panel, streaming, patch flow, version history | Core UX flows |
| **Tech Lead** | Integration, `api/db/schemas/` + ORM contracts, architecture decisions | Cohesion, quality |
| **QA** | `tests/api/`, `tests/workers/`, `frontend/e2e/` | >80% coverage, E2E critical path |

---

## 6. Backend Development Plan

### 6.1 Project Structure

```
singularity/
├── api/
│   ├── main.py               # App factory, lifespan, middleware stack
│   ├── config.py             # pydantic-settings, all env vars
│   ├── deps.py               # get_db, get_current_user, get_redis
│   ├── db/
│   │   ├── models.py         # All ORM models (SQLAlchemy)
│   │   ├── session.py        # Async engine, session factory
│   │   ├── schemas/          # Pydantic request/response models (auth, threads, research, …)
│   │   └── migrations/       # Alembic
│   │       ├── env.py
│   │       └── versions/
│   ├── auth/
│   │   ├── router.py         # POST /auth/google, POST /auth/refresh, POST /auth/logout
│   │   └── service.py        # verify Google ID token, JWT issue, user upsert
│   ├── research/
│   │   ├── router.py         # POST /jobs, GET /jobs/{id}, GET /jobs/{id}/events, POST /jobs/{id}/cancel
│   │   └── service.py        # Job lifecycle, idempotency, SSE pub
│   ├── reports/
│   │   ├── router.py         # CRUD, versions, export
│   │   └── service.py        # Ownership check, blob load
│   ├── threads/
│   │   ├── router.py         # POST /threads, POST /threads/{id}/messages (SSE)
│   │   └── service.py        # Context assembly, message persist, summary
│   ├── users/
│   │   ├── router.py         # GET /me, GET /me/stats, GET /me/usage
│   │   └── service.py        # Aggregate usage events, compute stats
│   └── middleware/
│       ├── auth.py
│       ├── rate_limit.py     # Redis sliding window
│       └── usage_emitter.py  # Async emit after response
├── workers/
│   ├── main.py               # ARQ WorkerSettings
│   ├── research_job.py       # run_research_job task
│   ├── patch_job.py          # run_patch_job (async patch via LLM)
│   └── summary_job.py        # thread rolling summary
├── storage/
│   ├── base.py               # BlobStore protocol
│   ├── s3.py                 # S3 / R2
│   └── local.py              # dev
└── patch/
    ├── service.py
    ├── slug.py
    └── validator.py
```

### 6.2 Database Schema

```sql
-- Users
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    google_sub      TEXT UNIQUE NOT NULL,       -- Google OAuth sub
    email           TEXT UNIQUE NOT NULL,
    name            TEXT,
    avatar_url      TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_login_at   TIMESTAMPTZ,
    daily_token_budget INTEGER NOT NULL DEFAULT 1000000,
    is_active       BOOLEAN NOT NULL DEFAULT true
);

-- Refresh Tokens
CREATE TABLE refresh_tokens (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash      TEXT UNIQUE NOT NULL,       -- SHA-256 of the raw token
    family_id       UUID NOT NULL,              -- rotation family (reuse = revoke all)
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at      TIMESTAMPTZ NOT NULL,
    revoked_at      TIMESTAMPTZ
);
CREATE INDEX idx_rt_user_id ON refresh_tokens(user_id);

-- Reports
CREATE TABLE reports (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title           TEXT,
    query           TEXT NOT NULL,
    strength        SMALLINT NOT NULL DEFAULT 5,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_reports_user_id ON reports(user_id, created_at DESC);

-- Report Versions (immutable)
CREATE TABLE report_versions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    report_id       UUID NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    version_num     INTEGER NOT NULL,
    content_inline  TEXT,                       -- NULL if blob
    content_uri     TEXT,                       -- S3 key if large (>500KB)
    content_hash    TEXT NOT NULL,              -- SHA-256, used as ETag
    char_count      INTEGER NOT NULL,
    patch_instruction TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (report_id, version_num)
);

-- Research Jobs
CREATE TABLE research_jobs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    report_id       UUID NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    idempotency_key TEXT,
    status          TEXT NOT NULL DEFAULT 'pending',  -- pending|running|done|failed|cancelled
    strength        SMALLINT NOT NULL DEFAULT 5,
    attempts        SMALLINT NOT NULL DEFAULT 0,
    max_attempts    SMALLINT NOT NULL DEFAULT 3,
    current_phase   TEXT,                       -- B|A|C|D for progress display
    error_detail    TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    started_at      TIMESTAMPTZ,
    finished_at     TIMESTAMPTZ,
    expires_at      TIMESTAMPTZ
);
CREATE UNIQUE INDEX idx_rj_idempotency ON research_jobs(user_id, idempotency_key)
    WHERE idempotency_key IS NOT NULL;

-- Threads
CREATE TABLE threads (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    report_id       UUID REFERENCES reports(id) ON DELETE CASCADE, -- NULL = pure chat
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    pinned_version_num INTEGER,
    summary         TEXT,
    summary_through_message_id UUID,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Messages
CREATE TABLE messages (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id       UUID NOT NULL REFERENCES threads(id) ON DELETE CASCADE,
    role            TEXT NOT NULL,              -- 'user' | 'assistant'
    content         TEXT NOT NULL,
    token_count     INTEGER,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_messages_thread ON messages(thread_id, created_at);

-- Usage Events (append-only, comprehensive)
CREATE TABLE usage_events (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    event_type      TEXT NOT NULL,  -- 'llm_call'|'report_generate'|'chat_message'|'patch'|'report_view'
    model           TEXT,
    prompt_tokens   INTEGER,
    completion_tokens INTEGER,
    cost_usd        NUMERIC(10,6),
    route           TEXT,           -- 'research_job'|'chat_qa'|'patch'|'thread_summary'
    report_id       UUID,
    job_id          UUID,
    thread_id       UUID,
    duration_ms     INTEGER,
    success         BOOLEAN,
    error_code      TEXT,
    -- Client context
    user_agent      TEXT,
    ip_address      INET,
    device_type     TEXT,           -- 'desktop'|'mobile'|'tablet'
    os              TEXT,           -- 'macOS'|'Windows'|'iOS'|'Android'|'Linux'
    browser         TEXT,           -- 'Chrome'|'Safari'|'Firefox'|'Edge'
    country         TEXT,           -- ISO-3166 from IP
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_ue_user_day  ON usage_events(user_id, created_at DESC);
CREATE INDEX idx_ue_event_type ON usage_events(user_id, event_type, created_at DESC);
```

### 6.3 API Contract

```
Auth:
  POST /api/v1/auth/google          { id_token } → TokenPair
  POST /api/v1/auth/refresh         { refresh_token } → TokenPair
  POST /api/v1/auth/logout          (revokes refresh token)

Users / Stats:
  GET  /api/v1/users/me             → UserProfile
  GET  /api/v1/users/me/stats       → { total_reports, total_tokens, cost_usd, streak_days, ... }
  GET  /api/v1/users/me/usage       ?range=7d|30d|90d → time-series for graphs
  GET  /api/v1/users/me/usage/models → model breakdown pie data
  GET  /api/v1/users/me/usage/devices → device/OS/browser breakdown

Research Jobs:
  POST /api/v1/research/jobs        { query, strength?, idempotency_key? } → JobCreated
  GET  /api/v1/research/jobs/{id}   → JobStatus
  GET  /api/v1/research/jobs/{id}/events  SSE → job_status|job_done|job_error
  POST /api/v1/research/jobs/{id}/cancel  → 202

Reports:
  GET  /api/v1/reports              cursor-paginated → ReportList
  GET  /api/v1/reports/{id}         → ReportMeta
  GET  /api/v1/reports/{id}/versions → VersionList
  GET  /api/v1/reports/{id}/versions/{v}  → { content, etag }
  POST /api/v1/reports/{id}/versions/{v}/patch  If-Match → 201|409|422
  GET  /api/v1/reports/{id}/versions/{v}/export  ?format=md|html → file

Threads:
  POST /api/v1/threads              { report_id?, pinned_version? } → ThreadCreated
  GET  /api/v1/threads/{id}         → ThreadWithMessages
  POST /api/v1/threads/{id}/messages  SSE → plan|step_start|token|step_end|done|error
```

### 6.4 Google OAuth Flow

```
Frontend (NextAuth.js)               Backend (FastAPI)
─────────────────────                ─────────────────
User clicks "Sign in with Google"
  → NextAuth redirects to Google
  → User consents
  → Google returns ID token to NextAuth
  → NextAuth stores session
  → Frontend calls POST /api/v1/auth/google
    with { id_token: "..." }
                                     Verifies token with Google (google-auth-library)
                                     Extracts: sub, email, name, picture
                                     UPSERT users ON CONFLICT(google_sub)
                                     Issues JWT access (15min) + refresh (30d)
                                     Returns TokenPair
  → Frontend stores tokens (httpOnly cookie or memory)
  → Redirects to /dashboard
```

### 6.5 Worker Architecture

```python
# workers/research_job.py
async def run_research_job(ctx, job_id: str) -> None:
    job = await db.get_job(job_id)
    if job.status in ("done", "cancelled"): return  # idempotent

    cancel_token = CancelToken(lambda: datetime.utcnow() > job.expires_at)

    async def phase_progress(phase: str, desc: str):
        await db.update_job_phase(job_id, phase)
        await redis_publish(job_id, "job_status", {"phase": phase, "description": desc})

    try:
        markdown = await run_pipeline(
            query=job.query, strength=job.strength,
            cancel_token=cancel_token,
            on_phase=phase_progress,
        )
        version = await create_report_version(db, storage, job.report_id, markdown)
        await db.update_job(job_id, status="done", finished_at=now())
        await redis_publish(job_id, "job_done", {"version_num": version.version_num})
    except Cancelled:
        await db.update_job(job_id, status="cancelled")
    except Exception as e:
        if job.attempts >= job.max_attempts:
            await db.update_job(job_id, status="failed", error=str(e)[:500])
            await redis_publish(job_id, "job_error", {"message": str(e)})
        else:
            raise  # ARQ retries with backoff
```

---

## 7. Frontend Development Plan

### 7.1 Stack

```
Next.js 14 (App Router) + TypeScript strict
Tailwind CSS + shadcn/ui
Framer Motion (animations)
NextAuth.js (Google OAuth)
Tanstack Query v5 (data fetching + cache)
Zustand (client state: report, selection, chat)
react-markdown + remark-math + rehype-katex (report rendering)
OpenAPI codegen client (from FastAPI /openapi.json)
Playwright (E2E tests)
```

### 7.2 Routes

```
/                       Landing — Google sign-in + product tagline
/dashboard              Post-login home — Chat bar (bottom) + Reports grid (top)
/reports/[id]           Report view — Markdown left, Chat panel right
/reports/[id]/history   Version history
/profile                Usage stats dashboard (graphs, model breakdown, device)
```

### 7.3 Landing Page Design Spec

- Full-viewport dark gradient (deep navy → near-black)
- Centered: product name, one-line tagline, large "Sign in with Google" button
- Background: subtle animated particle mesh or flowing gradient blobs (CSS/canvas)
- No nav, no clutter. One action.

### 7.4 Dashboard Design Spec

```
┌─────────────────────────────────────────────────────────┐
│  Singularity                            [avatar] [⚙]    │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Recent Projects                         [+ New]        │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐    │
│  │ Report title │ │ Report title │ │ Report title │    │
│  │ 2 days ago   │ │ 1 week ago   │ │ 3 weeks ago  │    │
│  │ 45k chars    │ │ 32k chars    │ │ 12k chars    │    │
│  └──────────────┘ └──────────────┘ └──────────────┘    │
│                                                         │
│  ─────────────────────────────────────────────────────  │
│  │  Ask anything or describe a research topic...    [→] │
│  ─────────────────────────────────────────────────────  │
└─────────────────────────────────────────────────────────┘
```

- Chat bar stays fixed at the bottom. On submit: if "Generate report" mode → creates research job with live progress overlay. If "chat" mode → opens a thread inline above the bar.
- Report cards: hover lifts with shadow, click → `/reports/[id]`
- Strength selector: inline popover before submit (1–10 slider, cost estimate)

### 7.5 Report View Design Spec

```
┌──────────────────────────────────┬────────────────────┐
│  ← Dashboard    Report Title  v3 │  Q&A with Report   │
├──────────────────────────────────┤                    │
│                                  │  [message bubbles] │
│  # Report Title                  │                    │
│  ## Section 1                    │                    │
│  Lorem ipsum...                  │                    │
│  [selected text → toolbar]       │  ───────────────── │
│                                  │  Ask about this... │
│  ## Section 2                    └────────────────────┘
│  ...
└──────────────────────────────────
```

- Chat panel slides in from the right (Framer Motion).
- Patch toolbar floats above selection.
- Report renders with syntax highlighting, math (KaTeX), tables.

### 7.6 Key Components

```
components/
├── auth/
│   └── GoogleSignInButton.tsx
├── dashboard/
│   ├── ReportCard.tsx          # Hover animation, status badge
│   ├── ReportGrid.tsx          # Masonry or uniform grid
│   ├── ChatBar.tsx             # Bottom bar, mode toggle, strength picker
│   └── JobProgressOverlay.tsx  # SSE consumer, phase display, animated loader
├── report/
│   ├── ReportViewer.tsx        # react-markdown, selection handler
│   ├── SelectionToolbar.tsx    # Floating edit/copy actions
│   ├── PatchModal.tsx          # Instruction input, diff preview
│   ├── VersionBadge.tsx        # vN badge + history link
│   └── ChatToReportButton.tsx  # "Generate report from conversation"
├── chat/
│   ├── ChatPanel.tsx           # Slide-in panel
│   ├── MessageBubble.tsx       # User / assistant
│   ├── StreamingMessage.tsx    # Token-by-token SSE render
│   ├── PlanDisplay.tsx         # Step-by-step plan display
│   └── SourceList.tsx          # Grounding citations
├── profile/
│   ├── UsageChart.tsx          # Recharts time-series (tokens/cost)
│   ├── ModelBreakdown.tsx      # Pie chart by model
│   └── DeviceBreakdown.tsx     # OS/browser bar chart
└── shared/
    ├── SSEConsumer.tsx         # useSSE hook wrapper
    ├── ErrorBoundary.tsx
    └── AnimatedPage.tsx        # Framer Motion page transition wrapper
```

### 7.7 Animations Spec (Framer Motion)

| Interaction | Animation |
|-------------|-----------|
| Page transition | `opacity: 0→1, y: 8→0, duration: 0.25s` |
| Report card hover | `scale: 1→1.02, shadow lift, duration: 0.15s` |
| Chat panel open | `x: 100%→0, duration: 0.3s, ease: easeOut` |
| Message bubble enter | `opacity: 0→1, y: 6→0, stagger 0.05s` |
| Streaming cursor | Blinking `|` at text end while streaming |
| Job progress phases | Phase label fades in/out, progress bar animates |
| Patch modal | Scale in from center `scale: 0.95→1` |
| Loading skeleton | Shimmer gradient sweep `@keyframes shimmer` |

---

## 8. Usage Tracking System

### 8.1 Tracking Strategy

Every meaningful server-side event emits a `UsageEvent`. This is **always async and non-blocking** — it runs after the response is sent.

```python
# api/middleware/usage_emitter.py

class UsageEmitterMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        # Fire-and-forget: never delays response
        asyncio.create_task(
            emit_usage_event(request, response)
        )
        return response

async def emit_usage_event(request: Request, response: Response):
    user_id = getattr(request.state, "user_id", None)
    if not user_id: return

    # Parse User-Agent
    ua = parse_user_agent(request.headers.get("user-agent", ""))

    # Geo from IP (cached in Redis, 1h TTL)
    country = await get_country_from_ip(request.client.host)

    event = UsageEvent(
        user_id=user_id,
        event_type=classify_route(request.url.path),
        duration_ms=request.state.duration_ms,
        success=response.status_code < 400,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host,
        device_type=ua.device_type,
        os=ua.os,
        browser=ua.browser,
        country=country,
    )
    await db.insert_usage_event(event)
```

### 8.2 LLM Cost Tracking

Each LLM call in the engine emits a structured cost event. We hook into this via a lightweight observer:

```python
# Injected into ExecutionContext before pipeline starts
context.on_llm_call = lambda event: task_queue.put_nowait(event)

# Worker drains queue after pipeline completes
for event in task_queue:
    await db.insert_usage_event(UsageEvent(
        user_id=job.user_id, job_id=job.id,
        event_type="llm_call",
        model=event.model,
        prompt_tokens=event.prompt_tokens,
        completion_tokens=event.completion_tokens,
        cost_usd=calculate_cost(event.model, event.prompt_tokens, event.completion_tokens),
        route="research_job",
    ))
```

### 8.3 Stats API Response Shape

```json
GET /api/v1/users/me/stats
{
  "total_reports": 47,
  "total_tokens": 4820000,
  "total_cost_usd": 12.45,
  "reports_this_week": 5,
  "tokens_today": 45000,
  "tokens_remaining_today": 955000,
  "streak_days": 7,
  "avg_report_strength": 6.2,
  "favorite_model": "grok-3",
  "most_active_hour": 14
}

GET /api/v1/users/me/usage?range=30d
{
  "series": [
    { "date": "2026-03-01", "tokens": 45000, "cost_usd": 0.12, "reports": 2 },
    ...
  ],
  "total_tokens": 1200000,
  "total_cost_usd": 3.20
}

GET /api/v1/users/me/usage/models
{
  "breakdown": [
    { "model": "grok-3", "tokens": 800000, "cost_usd": 2.10, "pct": 66 },
    { "model": "gemini-2.0-flash", "tokens": 400000, "cost_usd": 1.10, "pct": 34 }
  ]
}
```

---

## 9. Edge Cases and Failure Modes

### Research Jobs
| Scenario | Handling |
|----------|---------|
| Worker crashes mid-pipeline | Heartbeat miss → DLQ after 10 min. Next attempt picks up (idempotent, retries up to max_attempts). |
| User cancels mid-run | `POST /cancel` sets `expires_at=now()`. Engine checks cancel_token at phase boundaries. |
| Same query submitted twice | Idempotency key returns existing job (200, not 201) within 24h. |
| All LLM providers fail | After 3 retries across providers → job `failed`, error: `llm_unavailable`. |
| Job times out | ARQ `job_timeout=1800s`. Sets `failed`, `error: timeout`. |

### Patch
| Scenario | Handling |
|----------|---------|
| Selection not found verbatim | Fuzzy match (difflib >0.85). Still fails → 422. |
| LLM generates oversized output | Reject if new section >3× original. 422. |
| Concurrent patch by same user | ETag SELECT FOR UPDATE. Second writer → 409. |
| LLM injects HTML/script in MD | MD AST validation strips script tags. Reject if unsafe nodes present. |

### SSE
| Scenario | Handling |
|----------|---------|
| Client disconnects | Worker continues async. Client reconnects with `Last-Event-ID`, replays from cursor. |
| Redis pub/sub fails | SSE falls back to DB polling at 3s interval. |
| Proxy strips chunked encoding | `X-Accel-Buffering: no` header on all SSE responses. |
| SSE auth (EventSource can't send headers) | Short-lived SSE token (30s, signed) passed as query param. Generated by `GET /auth/sse-token`. |

### Auth
| Scenario | Handling |
|----------|---------|
| Google token expired/invalid | 401 with `code: invalid_google_token`. |
| Refresh token reuse after rotation | Revoke entire family. User must re-authenticate. |
| Account deactivated | `is_active=false` → 401. |

---

## 10. Infrastructure and Hosting

### Services

| Service | Dev | Production |
|---------|-----|------------|
| FastAPI | `uvicorn --reload` | Docker on Fly.io or Railway |
| ARQ Workers | Same container (1 worker) | Separate container (2–4 workers) |
| PostgreSQL | Docker Compose | Supabase or Neon (managed) |
| Redis | Docker Compose | Upstash Redis |
| Blob store | Local filesystem | Cloudflare R2 |
| Next.js | `next dev` | Vercel |
| Qdrant | In-memory | Qdrant Cloud |

### New Dependencies

```
# requirements_api.txt (additions to existing requirements.txt)
fastapi>=0.111
uvicorn[standard]>=0.29
sqlalchemy[asyncio]>=2.0
alembic>=1.13
asyncpg>=0.29
pydantic-settings>=2.2
arq>=0.25
redis>=5.0
httpx>=0.27
google-auth>=2.29          # Google ID token verification
authlib>=1.3               # OAuth2 flows
python-jose[cryptography]  # JWT
bcrypt>=4.1
python-multipart>=0.0.9
aioboto3>=12.3             # S3/R2 async
user-agents>=2.2.0         # UA parsing
```

### Docker Compose

```yaml
version: "3.9"
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: singularity
      POSTGRES_USER: singularity
      POSTGRES_PASSWORD: dev_password
    ports: ["5432:5432"]
    volumes: [postgres_data:/var/lib/postgresql/data]

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]

  api:
    build: { context: ., dockerfile: Dockerfile.api }
    command: uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
    ports: ["8000:8000"]
    depends_on: [postgres, redis]
    env_file: .env
    volumes: [.:/app]

  worker:
    build: { context: ., dockerfile: Dockerfile.api }
    command: python -m workers.main
    depends_on: [postgres, redis]
    env_file: .env
    volumes: [.:/app]

volumes:
  postgres_data:
```

---

## 11. How to Spawn the Agent Team in Claude Code

Claude Code supports multi-agent execution through **git worktrees** and **multiple terminal sessions**. Each agent runs as a separate `claude` process with an isolated copy of the repo.

### Method 1: Git Worktrees (Recommended — True Isolation)

```bash
# From the main repo dir
# Create a worktree + branch for each agent
git worktree add ../sing-infra      -b feat/infra
git worktree add ../sing-be-core    -b feat/be-core
git worktree add ../sing-be-feat    -b feat/be-features
git worktree add ../sing-fe-found   -b feat/fe-foundation
git worktree add ../sing-fe-ui      -b feat/fe-report-ui

# Then in each worktree, open Claude Code
# iTerm2: ⌘T for new tab, or use tmux
cd ../sing-infra     && claude
cd ../sing-be-core   && claude
cd ../sing-be-feat   && claude
cd ../sing-fe-found  && claude
cd ../sing-fe-ui     && claude
```

Each `claude` session has its own repo copy. They commit to their branch. Tech Lead merges.

### Method 2: tmux Multi-Pane (Fastest Setup)

```bash
# Install tmux if needed: brew install tmux
tmux new-session -s singularity

# Split into panes
# Ctrl+B, then %  (vertical split)
# Ctrl+B, then "  (horizontal split)
# Ctrl+B, then o  (switch pane)

# Pane 1: BE-1 Infra
cd /Users/nishant/Desktop/singularity && claude

# Pane 2: BE-2 Core API (after git worktree add)
cd ../sing-be-core && claude

# etc.
```

### Method 3: Non-Interactive Mode (Fully Automated)

```bash
# Run claude with a task description, no human in the loop
# Each runs in background
claude --dangerously-skip-permissions \
  -p "$(cat docs/agent_prompts/be_infra.md)" \
  --output-format stream-json \
  > logs/be_infra.log 2>&1 &

claude --dangerously-skip-permissions \
  -p "$(cat docs/agent_prompts/be_core.md)" \
  --output-format stream-json \
  > logs/be_core.log 2>&1 &

claude --dangerously-skip-permissions \
  -p "$(cat docs/agent_prompts/fe_found.md)" \
  --output-format stream-json \
  > logs/fe_found.log 2>&1 &
```

### Recommended Workflow

```
1. Tech Lead (this session) writes shared contracts first:
   - api/db/models.py       (ORM — BE agents agree on persistence schema)
   - api/db/schemas/        (Pydantic request/response layer)
   - api/config.py         (all env vars agreed)

2. Spawn BE-1 (Infra) immediately — no dependencies.

3. Spawn BE-2 (Core API) after contracts are written.

4. Spawn FE-1 (Foundation) immediately — frontend has no backend dep yet.

5. Spawn BE-3 (Features) after BE-2 finishes auth + DB.

6. Spawn FE-2 (Report UI) after FE-1 shell + BE-2 APIs are ready.

7. QA runs last — writes tests against the complete API.
```

### Agent Prompt Template

When spawning each agent, pass a prompt like:

```
You are [ROLE] on the Singularity platform team.
Read docs/PLATFORM_DEVELOPMENT_GUIDE.md for the full spec.
Your specific task: [TASK DESCRIPTION]
Files you own: [FILE LIST]
Files to READ but NOT modify: [FILE LIST]
Definition of done: [CHECKLIST]
Write production-quality code. No TODOs, no stubs. Commit when done.
```
