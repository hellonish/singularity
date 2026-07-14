# Singularity

Singularity is being rebuilt around a new API and engine. This branch contains
the API v2 data foundation: a portable FastAPI + SQLAlchemy schema that starts
on SQLite and can later move to PostgreSQL.

## Current scope

The API owns the durable data model, SQLite development lifecycle, local object
store, and HTTP route templates. Production uses Alembic before API/worker
startup. The bounded research path is executable through the CLI and ARQ
worker; other engine work remains behind stable service boundaries.

Identity has two modes, selected by `SINGULARITY_AUTH_MODE`:

- `bearer` (default) — Google-federated browser authentication plus automatic
  CLI device authentication. Both receive a short-lived access JWT plus a
  rotating refresh token; every user-scoped endpoint requires
  `Authorization: Bearer <access_jwt>`. The CLI route needs only the server's
  JWT secret, while Google login also needs its OAuth client id.
- `header` — the temporary `X-User-ID` boundary for local curl and the
  deterministic test suite. Create a user with `POST /users`, then send its ID
  in that header.

Both modes resolve to the same `User` through a single dependency
(`api/dependencies.py`), so routers and service calls are identical regardless
of mode.

Browser clients are enabled by configuring `SINGULARITY_CORS_ALLOW_ORIGINS`
(comma-separated). It is empty by default, leaving CORS off.

## Data model

```text
User
├── Chats (one-to-many)
│   ├── Messages (one-to-many)
│   └── Chat summaries (one-to-many)
├── Usage account (one-to-one)
│   ├── Daily / weekly / monthly rollups (one-to-many)
│   └── Usage history events (one-to-many)
├── Reports (one-to-many)
│   ├── Report versions (one-to-many)
│   └── Chats (one-to-many, optional report link)
├── Research runs (one-to-many, optionally linked to a report)
└── Refresh tokens (one-to-many)
```

Important design choices:

- UUIDs are stored as portable 36-character strings, avoiding SQLite-specific
  behavior while preserving stable IDs for a later PostgreSQL move.
- Core relationships are normalized and protected by foreign keys, unique
  constraints, and query indexes.
- Usage has one durable account per user, queryable day/week/month rollups, and
  append-only event history for future billing and analytics.
- JSON extension fields exist on each domain model for additive features without
  forcing a premature schema migration.
- Chats may have no report, or may be linked to one report; a report can have
  many chats.
- Report-version content is written through a small object-store interface. It
  uses the local filesystem now and has an isolated future adapter point for
  Supabase S3.

## Route templates

All routes are available in the generated OpenAPI UI at `/docs`.

| Resource | Routes | Current behavior |
| --- | --- | --- |
| System | `GET /health`, `GET /storage/health` | Reports application and configured storage health. |
| Users | `POST /users`, `GET/PATCH/DELETE /users/me` | Creates users and their one-to-one usage account; deletion is a soft delete. |
| Chats | `GET/POST /chats`, `GET/PATCH/DELETE /chats/{id}` | Creates, lists, updates, and archives chats. |
| Auth | `POST /auth/google`, `POST /auth/cli-device`, `POST /auth/refresh`, `POST /auth/logout` | Supports interactive Google login and zero-interaction CLI device sessions, issues an access JWT + rotating refresh token, and revokes tokens (family-wide on reuse). |
| Messages | `GET/POST /chats/{id}/messages`, `POST /chats/{id}/messages/stream` | Persists the user message, streams the real engine `ChatAgent` reply as `accepted`/`delta`/`completed` SSE events, and persists the assistant reply. |
| Summaries | `GET/POST /chats/{id}/summaries` | Stores durable chat-summary checkpoints. |
| Reports | `GET/POST /reports`, `GET /reports/{id}`, `GET /reports/{id}/stream` | Creates and lists report metadata; the stream endpoint replays the latest stored report version over SSE (or `report.pending` when none exists yet). |
| Versions | `GET/POST /reports/{id}/versions`, `GET /reports/{id}/versions/{version_id}/content` | Saves version content into local object storage and exposes it as Markdown. |
| Research | `GET/POST /research/runs`, `GET /research/runs/{id}`, `POST /research/runs/{id}/cancel`, `GET /research/runs/{id}/events` | Creates bounded LangGraph research runs, persists replayable events, and optionally dispatches them to the ARQ worker. |
| LLM / BYOK | `GET/POST/PATCH /llm/credentials`, `GET /llm/credentials/{id}/models`, `POST /llm/completions` | Stores encrypted Groq credentials, discovers models with that credential, and runs request-scoped completions. |

`POST /chats` is limited to 3 requests/second per user, message sends (normal
and streamed together) to 3 requests/second per user, and `POST /reports` to
1 request/second per user. Exceeding a limit returns `429` with `Retry-After`.
The current limiter is in-process; move its counters to Redis before running
multiple API instances.

## Bounded research workflow

`engine/research_workflow/` contains the LangGraph state contracts and bounded runtime:

- QA may add at most two research nodes per section per cycle.
- Each research node may make at most four external tool calls: one search,
  two page fetches, and one optional recovery call.
- Strength controls the overall cycle, node, and runtime caps; it does
  not increase either per-section QA suggestions or per-node tool calls.
- `api/research_worker.py` is the ARQ entrypoint. It assembles the BYOK LLM
  adapter, Modal executor, QA reviewer, vector scope, structured writer, and
  LangGraph checkpointer directly from the persisted run configuration.
- Use `Last-Event-ID` when reconnecting to `/research/runs/{id}/events`; events
  are replayed from the durable `research_run_events` table.
- The API rejects new research runs with `503` if its worker is disabled, so a
  request is never accepted into a queue that has no consumer.

Run the deterministic CLI smoke workflow without a provider key, Modal
deployment, or frontend:

```bash
python -m engine.research_workflow.cli --demo --strength 1 --output-dir .artifacts/research \
  "How does bounded research work?"
```

The deterministic smoke command writes `research-document.json` and
`research-report.md`. In the terminal REPL, use `/mode` and choose **Research**;
each subsequent plain-text prompt runs the live LangGraph workflow with the
selected provider model and deployed Modal web tools, then renders the complete
report directly in the terminal. The hosted API owns Modal, Redis, the research
worker, durable events, and the report artifact; the CLI only streams progress
and the completed Markdown. It requires a saved key for the selected provider.
Choose **Chat** in `/mode` to return to normal conversational chat.
For live API execution, set the credential encryption key, Groq pricing rates,
and `SINGULARITY_RESEARCH_WORKER_ENABLED=1`; production Compose starts the
Alembic migration job and ARQ worker automatically.

### Real-inference test mode (curl only)

A gated test mode runs the full production path — real BYOK LLM calls and real
Modal web tools — but shrinks a run to the minimum needed to prove the wiring:
exactly **one node, one `web_search`, and one `web_fetch`**, with no QA cycle.
It exists so you can pay for one cheap real run instead of a full report.

It is off by default and requires **both** a server flag and a per-request
field, so it can never engage in normal operation:

- Server: `SINGULARITY_RESEARCH_TEST_MODE=1` (in addition to the usual
  `SINGULARITY_RESEARCH_WORKER_ENABLED=1`, a running Redis + ARQ worker, and a
  deployed Modal function with `SINGULARITY_MODAL_ENABLED=1`).
- Request: `"test_mode": true` in the `POST /research/runs` body.

If `test_mode` is sent while the server flag is off, the run is rejected with
`403` (never silently upgraded to a full run). When enabled, the minimal
profile is applied regardless of the requested `strength`.

```bash
# Server started with:
#   SINGULARITY_AUTH_MODE=header SINGULARITY_RESEARCH_WORKER_ENABLED=1 \
#   SINGULARITY_RESEARCH_TEST_MODE=1 SINGULARITY_MODAL_ENABLED=1 uvicorn api.main:app
# plus a running Redis, ARQ worker (api/research_worker.py), and deployed Modal function.

USER_ID=$(curl -s -X POST localhost:8000/users \
  -H 'Content-Type: application/json' -d '{"display_name":"RT"}' | jq -r '.id')

CRED_ID=$(curl -s -X POST localhost:8000/llm/credentials \
  -H 'Content-Type: application/json' -H "X-User-ID: $USER_ID" \
  -d '{"provider":"<provider>","api_key":"<your_real_key>","default_model_id":"<model_id>"}' | jq -r '.id')

RUN_ID=$(curl -s -X POST localhost:8000/research/runs \
  -H 'Content-Type: application/json' -H "X-User-ID: $USER_ID" \
  -d "{\"query\":\"What is retrieval-augmented generation?\",\"provider_credential_id\":\"$CRED_ID\",\"test_mode\":true}" \
  | jq -r '.id')

# Stream the run to completion (real LLM + 1 search + 1 fetch):
curl -N "localhost:8000/research/runs/$RUN_ID/events" -H "X-User-ID: $USER_ID"
```

## Backend SSE verification

Start the API in the `header` identity mode so the `X-User-ID` walkthrough
works without a Google token: `SINGULARITY_AUTH_MODE=header uvicorn
api.main:app --reload`. Create a temporary local user and resources (these
commands require `jq`):

```bash
USER_ID=$(curl -s -X POST http://localhost:8000/users \
  -H 'Content-Type: application/json' \
  -d '{"display_name":"SSE Test"}' | jq -r '.id')

CHAT_ID=$(curl -s -X POST http://localhost:8000/chats \
  -H 'Content-Type: application/json' \
  -H "X-User-ID: $USER_ID" \
  -d '{"title":"Streaming chat"}' | jq -r '.id')

REPORT_ID=$(curl -s -X POST http://localhost:8000/reports \
  -H 'Content-Type: application/json' \
  -H "X-User-ID: $USER_ID" \
  -d '{"title":"Streaming report"}' | jq -r '.id')
```

Use `curl -N` to disable client-side buffering and watch events arrive:

```bash
curl -N -X POST "http://localhost:8000/chats/$CHAT_ID/messages/stream" \
  -H 'Content-Type: application/json' \
  -H "X-User-ID: $USER_ID" \
  -d '{"content":"Show me a streamed response"}'

curl -N "http://localhost:8000/reports/$REPORT_ID/stream" \
  -H "X-User-ID: $USER_ID"
```

The chat stream runs the real engine `ChatAgent`, so the chat must have an
active BYOK credential (create one with `POST /llm/credentials` and pass its id
as `provider_credential_id` when creating the chat); without one the stream
endpoint returns `422`. The report stream replays the latest stored report
version, emitting a single `report.pending` event when a report has no version
yet. `SINGULARITY_SSE_DUMMY_DELAY_SECONDS` (default `0.15`) still paces the
per-chunk delay for the report replay.

## Terminal engine

The REPL lives independently in `engine/cli` and mounts terminal agents through
a small adapter registry. The distributable CLI is a thin client for the
hosted Singularity API: database, auth-session bootstrap, Redis, research
workers, and Modal tools stay server-managed. Install and start it without a
project `.env`:

```bash
pipx install .
singularity
```

For repository development, `python -m engine.cli` remains equivalent. On first
launch, use `/key`, choose **Set or replace key**, and enter the selected
provider key in the hidden prompt. That is the only end-user setup. The CLI
automatically creates a renewable device API session, synchronizes the BYOK
credential over TLS, and saves its local device/session state alongside the key
in the private global configuration.

Inside the REPL, plain text streams a chat response. `/provider`, `/models`,
`/effort`, and `/key` open arrow-key selectors; `/status`, `/reset`, `/clear`,
`/help`, and `/quit` manage the current session. New sessions default to
`medium` effort. Groq, DeepSeek, and OpenRouter are supported. Provider keys,
the selected provider/model/effort, and renewable device-session state are persisted globally in
`~/.config/singularity/terminal.json` with private user-only permissions; it is
never written to the repository. Chat and research are persisted by the API.
The default hosted endpoint is `https://singularity.hellonish.dev/api`; developers
may override it with `SINGULARITY_API_URL`. Direct provider/Modal execution is
retained only for repository development via
`SINGULARITY_CLI_BACKEND=local`; shipped users do not configure Modal.
If the default hosted endpoint is unavailable or does not expose CLI device
authentication, the CLI falls back to `http://127.0.0.1:8000`. This fallback
applies only to the implicit default; an explicit `SINGULARITY_API_URL` is
never overridden.

The hosted API resolves the encrypted credential and model for each request,
retrieves the model's live context/output limits, preserves the user message,
and trims only optional context. Provider deltas travel to the CLI through the
API's SSE contract and are rendered as they arrive; plaintext BYOK values are
never returned by the API.

## Groq BYOK

The application never stores a Groq key in an LLM provider object. A user adds
their key once through `POST /llm/credentials`; it is encrypted at rest using
`SINGULARITY_CREDENTIAL_ENCRYPTION_KEY`. Each model-list or completion request
loads and decrypts the selected credential only in memory, creates a temporary
Groq client, then discards the client and key reference.

`POST /llm/completions` accepts a credential ID and optional model ID, never an
API key:

```json
{
  "message": "Explain this architecture",
  "provider_credential_id": "cred_123",
  "model_id": "openai/gpt-oss-20b"
}
```

The resolved model uses this precedence: request model → selected chat model →
credential default model → `SINGULARITY_GROQ_FALLBACK_MODEL`. Every completion
validates the resolved model through Groq's authenticated Models API before it
runs. Set `SINGULARITY_CREDENTIAL_ENCRYPTION_KEY` to a stable Fernet key before
accepting credentials; changing it makes existing ciphertext undecryptable.

The default test suite uses only real local API, database, and filesystem
dependencies. The Groq end-to-end test is intentionally opt-in because it
makes real provider requests: set `SINGULARITY_RUN_LIVE_TESTS=1`, provide
`SINGULARITY_TEST_GROQ_API_KEY`, and run `pytest -m integration`.

## Modal trusted tool deployment

Deploy the trusted tool Function separately from the API after authenticating
the Modal CLI outside this repository:

```bash
modal deploy engine/modal_app/chat_tools.py --env main
```

The deployed app is `singularity-chat-tools` and its Function is
`execute_chat_tool`. Provision the named `singularity-tool-providers` secret in
Modal for optional external tool-provider credentials. Do not put Groq/BYOK,
database, internal API, deployment, or Modal-control credentials in that
secret. The terminal client sends only validated skill-scoped invocation data
and enforces its lower effort timeout locally; the Function itself has a
420-second ceiling. To run the separate deployed-function smoke test, set
`SINGULARITY_RUN_MODAL_TESTS=1` and run `pytest -m integration`.

Trusted chat operations now include `web_search`, guarded `web_fetch`,
`browser_render`, `calculator`, and `current_time`, alongside the existing
research providers and parsers. `web_search` discovers URLs; `web_fetch` reads
and extracts one public HTTP page; `browser_render` is the JavaScript fallback.
URL-reading operations reject private, local, reserved, link-local, embedded-
credential, non-HTTP, and nonstandard-port targets.

Repository inspection and generated dataset analysis are deliberately excluded
from the trusted Function and local CLI planner. They use separate no-secret
Modal Sandbox adapters: repository inspection permits only public GitHub clone
traffic and predefined inspection operations, while dataset analysis has
networking blocked and receives only a CSV plus generated Python. Production
vector retrieval is also excluded from CLI and Modal; it executes through the
authenticated API `RetrievalService` after relational ownership checks.

## LangSmith observability

The CLI chat agent uses LangSmith's standalone SDK directly; it does not use
LangChain or LangGraph. Once configured, each chat turn records nested spans
for local context selection, prompt budgeting, tool planning and Modal tool
calls, Groq model lookup and streaming generation, and local compaction.

Set these values outside source control:

```bash
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=...
LANGSMITH_PROJECT=singularity-dev
```

`LANGSMITH_ENDPOINT` is optional for a self-hosted deployment. By default,
Singularity records only hashes, counts, durations, and operational metadata.
Set `SINGULARITY_LANGSMITH_CAPTURE_CONTENT=true` only in an approved
development environment to include sanitized messages and final outputs. The
adapter never captures Groq/BYOK keys, database credentials, raw tool
arguments, or raw provider errors, and LangSmith credentials are never sent to
Modal. Tracing is fail-open: unavailable observability cannot interrupt chat.

For machine-consumed responses, include `structured_output` with a JSON Schema.
The API accepts only Groq strict-mode models (`openai/gpt-oss-20b` and
`openai/gpt-oss-120b`), requires every field to be marked required with
`additionalProperties: false`, sends Groq `json_schema` with `strict: true`,
then parses and validates the returned JSON against the same schema before
responding. It rejects unsupported models, invalid strict schemas, malformed
JSON, and schema-invalid output.

## Groq failure handling

Provider failures never expose a Groq API key or upstream error body. The LLM
API returns a stable error object with `code`, `message`, and `retryable`.
Rate limits return `429` and pass Groq's `Retry-After` value through; temporary
network/provider/capacity failures return retryable `503`; invalid credentials,
permission failures, rejected requests, and exhausted credits return actionable
non-retryable `422`. The completion layer does not automatically retry a
generation because a connection failure can be ambiguous—the provider may have
already processed it. A future durable job queue should retry only errors marked
`retryable`, using an idempotency key.

## Local development

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Optional: defaults to sqlite+aiosqlite:///./singularity.db
export SINGULARITY_DATABASE_URL=sqlite+aiosqlite:///./singularity.db
export SINGULARITY_STORAGE_ROOT=./data/objects

# Bearer auth (default) needs both; set a Google OAuth client id and a JWT
# secret. Use SINGULARITY_AUTH_MODE=header to fall back to the X-User-ID flow.
export SINGULARITY_GOOGLE_CLIENT_ID=...
export SINGULARITY_JWT_SECRET=...

# Allow a browser client (empty by default = CORS off):
export SINGULARITY_CORS_ALLOW_ORIGINS=http://localhost:3000

uvicorn api.main:app --reload
```

The database tables are created automatically in development. Later, before
using a shared PostgreSQL deployment, introduce versioned migrations from this
clean baseline instead of importing the removed v1 migration history.

## Verification

```bash
python -m pytest tests/database/test_schema.py -q -o addopts=

# Full existing test suite:
python -m pytest -q
```
