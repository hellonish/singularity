# Singularity

An AI-powered deep-research platform that orchestrates a multi-agent LLM pipeline to plan, retrieve, write, and polish fully-cited research reports — with real-time streaming, per-report Q&A chat, and production deployment on a $25/month AWS VM.

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Browser (Next.js 16)                         │
│  Dashboard │ Report Viewer │ Chat Panel │ Profile (BYOK Keys)       │
└──────┬──────────────┬──────────────┬──────────────┬─────────────────┘
       │              │              │              │
       ▼              ▼              ▼              ▼
┌──────────────────────────────────────────────────────────────────────┐
│                     Caddy (auto-SSL, Let's Encrypt)                  │
│                      :80/:443 → reverse proxy                        │
└──────┬──────────────────────┬────────────────────────────────────────┘
       │ /api/*               │ /*
       ▼                      ▼
┌──────────────────┐  ┌───────────────────┐
│   FastAPI API    │  │  Next.js Frontend  │
│   (256 MB cap)   │  │   (128 MB cap)     │
└──┬───┬───┬───┘  └───────────────────┘
   │   │   │
   │   │   └──── UsageEmitter (fire-and-forget analytics)
   │   └──────── RateLimitMiddleware (Redis sliding window)
   └──────────── AuthMiddleware (JWT + Google OAuth)
       │
       ▼ enqueue_job()
┌──────────────────┐
│   ARQ Worker     │
│   (1 GB cap)     │
│                  │
│  Phase B ──────▶ Planning: 3 Managers propose trees → Lead synthesizes
│       │          (asyncio.gather — parallel)
│       ▼
│  Phase A ──────▶ Retrieval: tree-informed skill selection → 18 skills
│       │          → source gate → chunk + embed → Qdrant
│       ▼
│  Phase C ──────▶ Writing: bottom-up section workers + augmentation
│       │          loops + faithfulness checks
│       ▼
│  Phase D ──────▶ Polish: deterministic cleanup + LLM formatting
│                  │
│                  └─── User's BYOK model + API key for EVERY LLM call
└──┬───────┬───────┘
   │       │
   ▼       ▼
┌──────┐ ┌──────────────┐
│Redis │ │  PostgreSQL   │
│128MB │ │    256MB       │
└──────┘ └──────────────┘
```

---

## Interesting Engineering Decisions

### 1. Planning Before Retrieval

The pipeline phases are intentionally ordered B → A → C → D (out of alphabetical order). Planning runs **before** retrieval because the original DAG orchestrator (retrieval-first) produced drifted, unfocused evidence — it gathered sources against a vague topic and then tried to shape a report around whatever it found.

By committing to a section tree first, every retrieval query targets a real planned section. The Lead agent synthesizes three independent Manager proposals into a final tree, and then the Retriever maps skills to specific leaf sections. This costs extra LLM calls upfront (4 for planning) but dramatically improves evidence relevance and reduces wasted retrieval budget at high strengths.

### 2. fastembed Over sentence-transformers

The original embedding pipeline used `sentence-transformers/all-MiniLM-L6-v2`, which pulls in PyTorch (~1.4 GB). On a t3-small with 2 GB RAM and six Docker containers sharing that memory, 1.4 GB of embedding library was a non-starter — the worker OOM'd after the planning phase.

The swap to `fastembed` runs the same `all-MiniLM-L6-v2` model via ONNX Runtime instead of PyTorch. Same 384-dim embeddings, same cosine similarity quality, but the binary footprint dropped from ~1.4 GB to ~90 MB. All blocking ML and Qdrant operations also moved to a thread pool with timeouts, so the async event loop never starves during embedding or upsert calls.

### 3. SSE Tokens Are Separate 30-Second JWTs

SSE endpoints accept authentication via a query parameter (`?token=...`) because `EventSource` in the browser doesn't support custom headers. Putting a long-lived access token (15 minutes) in a URL is a bad idea — URLs get logged, cached, and appear in browser history.

Instead, the API exposes `GET /api/v1/auth/sse-token` which issues a single-use JWT with `type=sse` and a 30-second expiry. The frontend calls this endpoint right before opening the `EventSource`, so the token in the URL is short-lived enough to be practically useless if leaked. The middleware stack skips Bearer validation on `/events` paths and validates the SSE token independently.

### 4. Redis Sorted-Set Sliding Window Instead of a Fixed Counter

Rate limiting uses `ZREMBYRANGE` + `ZCARD` + `ZADD` in a single Redis pipeline transaction. Each request adds its timestamp to a sorted set keyed by user ID; expired entries are trimmed before counting.

A naive fixed counter (INCR + EXPIRE) creates a problem at window boundaries — 60 requests at 0:59 followed by 60 requests at 1:01 passes the check despite 120 requests in two seconds. The sorted-set approach provides a true sliding window with no boundary artifacts, at the cost of slightly more Redis memory per user (one sorted set per rate-limited client).

The rate limiter also **fails open**: if Redis is unreachable, requests pass through with a logged warning instead of 500-ing every API call. This was chosen because a Redis outage shouldn't take down the entire application — degraded rate limiting is preferable to a full outage.

### 5. Orphan Recovery on Worker Startup

Background workers can crash mid-job (OOM, LLM timeout, deployment restart). When the new worker process starts, it runs `_recover_orphaned_jobs()` which queries for all jobs in `running` or `pending` state, marks them `failed`, and publishes `job_error` SSE events.

Without this, orphaned jobs sit in `running` state forever on the frontend — the progress spinner never stops, and the user has no way to know the job died. The recovery gives immediate feedback ("Worker process restarted unexpectedly. Please retry.") and frees the user's concurrency slot so they can submit again. The `pending` state was added to the recovery query after discovering that jobs queued right before a crash never transitioned to `running` but still blocked the user's concurrent job count.

### 6. Pure BYOK — The Platform Never Pays for Inference

Every LLM call in the pipeline uses the user's own API key and their chosen model. The worker resolves the user's BYOK key for the selected provider at job start, creates a single LLM client, and passes it to every agent — planner, managers, lead, workers, retriever, source gate, and polisher all use the same client.

This means the infrastructure cost is fixed at ~$26/month regardless of how many users run research or which models they choose. Users can pick from 10 models across 3 providers (xAI Grok, Google Gemini, DeepSeek), and their keys are Fernet-encrypted at rest in PostgreSQL, decrypted only at job runtime.

---

## Build & Run

### Prerequisites

- Python 3.12+
- Node.js 20+
- Docker & Docker Compose
- PostgreSQL 16, Redis 7 (provided via Docker Compose)

### Local Development

```bash
# Clone
git clone https://github.com/hellonish/singularity.git
cd singularity

# Backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements_api.txt

# Frontend
cd frontend && npm install && cd ..

# Environment
cp .env.example .env
# Fill in your API keys, OAuth credentials, etc.

# Start infrastructure
docker compose up postgres redis -d

# Run database migrations
alembic upgrade head

# Start API server
uvicorn api.main:app --reload --port 8000

# Start background worker (separate terminal)
python -m workers.main

# Start frontend (separate terminal)
cd frontend && npm run dev
```

### Production Deployment (AWS EC2)

```bash
# On a fresh t3-small:
git clone https://github.com/hellonish/singularity.git
cd singularity
cp .env.production .env
# Edit .env with production values

# Deploy
bash deploy/deploy.sh
docker compose -f docker-compose.prod.yml up -d
```

The deploy script handles Docker Hub image pulls, environment validation, and volume setup. Production uses pre-built images — no on-server compilation.

### CLI (without the web app)

```bash
# Phase-5 pipeline (primary) — writes final_report.md in the current directory
python -m agents.orchestrator.cli "your research question" --strength 2 --audience expert --api-key YOUR_KEY

# Interactive chat REPL
python -m agents.chat.cli
python -m agents.chat.cli --model grok-3
```

---

## The Cost Model

| Resource | Monthly Cost |
|----------|-------------|
| AWS t3-small (2 vCPU, 2 GB RAM) | ~$25 |
| Qdrant Cloud (free tier) | $0 |
| Domain + SSL (Caddy / Let's Encrypt) | ~$1 |
| LLM inference | **$0** (users bring their own keys) |
| **Total** | **~$26/month** |

Six Docker containers share 2 GB of RAM with hard memory caps:

| Container | Memory | Notes |
|-----------|--------|-------|
| Caddy | 64 MB | Reverse proxy + auto-SSL |
| PostgreSQL 16 | 256 MB | Tuned: shared_buffers=64MB, work_mem=2MB |
| Redis 7 | 128 MB | LRU eviction at 96MB, AOF persistence |
| FastAPI API | 256 MB | Async throughout (asyncpg, aiohttp, arq) |
| ARQ Worker | 1 GB | Embedding model + LLM call headroom |
| Next.js | 128 MB | Standalone build output |

**Total committed: ~1.8 GB** on a 2 GB box. Every container has healthchecks. The system runs 4 concurrent research jobs globally, 2 per user, with a 30-minute timeout per job.

---

## What's Inside

| | |
|---|---|
| Backend | 19,000 lines of Python across 207 files |
| Frontend | 6,500 lines of TypeScript across 42 files |
| Skills | 44 pluggable (18 retrieval + 18 analysis + 8 output) |
| Data connectors | 14 tools (ArXiv, PubMed, GitHub, SEC EDGAR, YouTube, etc.) |
| LLM providers | 3 (xAI Grok, Google Gemini, DeepSeek) — 10 models |
| API endpoints | 31 REST + SSE endpoints |
| Database | 8 tables, 12 indexes (including 1 partial unique), 6 migrations |
| Middleware | 4 layers: Auth → RateLimit → UsageEmitter → CORS |
| Build time | 13 days, 65 commits, 1 engineer |

---

## Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md) — current-state architecture reference
- [ENGINEERING_SHOWCASE.md](ENGINEERING_SHOWCASE.md) — full engineering breakdown with metrics
- [docs/PLATFORM_DEVELOPMENT_GUIDE.md](docs/PLATFORM_DEVELOPMENT_GUIDE.md) — comprehensive development guide
