# API Contract — Chat & Research Modes

Reference for frontend integration. Covers the two primary product paths — **Chat**
(live, synchronous streaming) and **Research** (durable, background job) — plus the
shared auth and BYOK-credential prerequisites they both depend on.

Source of truth: `api/routers/*.py`, `api/schemas.py`, `api/services/*`. If this doc
and the code disagree, the code wins — update this file.

---

## 1. Conventions

- **Base URL** (local): `http://localhost:8000`
- **Content type**: `application/json` for all request bodies.
- **IDs**: opaque strings (UUIDs). Never parse or construct them client-side.
- **Timestamps**: ISO-8601 UTC.
- **Streaming**: Server-Sent Events (`text/event-stream`). Each event has an
  `event:` name, a JSON `data:` payload, and (for replayable streams) an `id:`.

### Auth

Two modes, set server-side by `SINGULARITY_AUTH_MODE`:

| Mode | Header the frontend sends | Use |
|---|---|---|
| `bearer` (default, production) | `Authorization: Bearer <access_jwt>` | Real users. JWT issued by `POST /auth/google`. |
| `header` (local/dev/tests) | `X-User-ID: <user_id>` | curl walkthroughs and the deterministic test suite. |

All endpoints below require one of these headers. In production the frontend uses
the **bearer** flow; `X-User-ID` is a dev-only shortcut.

**Bearer token lifecycle:**

- `POST /auth/google` `{ "id_token": "<google_id_token>" }` → `{ access_token, refresh_token, expires_in }`
- `POST /auth/refresh` `{ "refresh_token": "<refresh_token>" }` → new `TokenPair`
- `POST /auth/logout` `{ "refresh_token": "<refresh_token>" }` → `204`

Access tokens are short-lived (default 15 min); refresh before expiry.

### Standard error shape

FastAPI returns:

```json
{ "detail": "human-readable reason" }
```

| Status | Meaning for the frontend |
|---|---|
| `401` | Missing/invalid auth header or token. Re-authenticate. |
| `404` | Resource not found **or** not owned by the caller (ownership failures are 404, not 403, by design). |
| `422` | Validation failure (bad body) **or** chat has no BYOK credential (see Chat). |
| `503` | Research worker not enabled server-side. |
| `403` | `test_mode` requested but server flag off. |

Streaming endpoints report **in-stream failures** as a terminal event
(`message.error`, `research.failed`) rather than an HTTP error, because the stream
has already started with a `200`.

---

## 2. Prerequisite — BYOK provider credential

Both modes run real LLM calls with the **user's own key** (BYOK). The plaintext key
is sent once, encrypted at rest, and never returned. The frontend references it by
**id** thereafter.

### `POST /llm/credentials`

Request:

```json
{
  "provider": "groq",              // "groq" | "deepseek" | "openrouter"
  "api_key": "<user_key>",         // write-only; never echoed back
  "label": "My Groq key",          // optional
  "default_model_id": "openai/gpt-oss-20b"  // optional
}
```

Response `201` (`ProviderCredentialRead`) — note **no `api_key`**:

```json
{
  "id": "cred_...",
  "provider": "groq",
  "label": "My Groq key",
  "key_fingerprint": "…",         // safe to display; not the key
  "default_model_id": "openai/gpt-oss-20b",
  "status": "active",
  "created_at": "…", "updated_at": "…"
}
```

Other credential endpoints:

- `GET /llm/credentials` → list (`ProviderCredentialRead[]`)
- `PATCH /llm/credentials/{id}` → update label / default_model_id / status
- `GET /llm/credentials/{id}/models` → `AvailableModelRead[]` — live model list from
  the provider (`{ id, owned_by }`). Use this to populate a model picker.

`model_id` must be a model the chosen provider actually serves; the provider
validates it. Groq currently supports strict-mode `openai/gpt-oss-20b` and
`openai/gpt-oss-120b`.

---

## 3. Chat mode — live synchronous streaming

Chat runs the engine `ChatAgent` **inside the HTTP request** and streams text deltas
straight back. Short-lived (seconds); on disconnect, just resend.

### 3.1 Create a chat

`POST /chats` — body `ChatCreate`:

```json
{
  "title": "My chat",                       // optional
  "provider_credential_id": "cred_...",     // REQUIRED to stream (see note)
  "report_id": "rep_...",                   // optional — attach a report (see §3.5)
  "model_id": "openai/gpt-oss-20b"          // optional; falls back to credential default
}
```

Response `201` (`ChatRead`):

```json
{
  "id": "chat_...",
  "user_id": "...",
  "report_id": "rep_..." | null,
  "provider_credential_id": "cred_..." | null,
  "title": "My chat",
  "status": "active",
  "last_message_at": null,
  "created_at": "…", "updated_at": "…"
}
```

> **A chat must carry an active `provider_credential_id` to stream.** Without one,
> `POST /chats/{id}/messages/stream` returns **`422`** before any stream opens. Set it
> at create time, or later via `PATCH /chats/{id}`.

### 3.2 Chat CRUD

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/chats` | List the user's chats (newest first). |
| `GET` | `/chats/{id}` | Fetch one chat. |
| `PATCH` | `/chats/{id}` | Update title / status / report_id / provider_credential_id / model_id. |
| `DELETE` | `/chats/{id}` | Archive (soft) — sets `status: "archived"`, returns the chat. |
| `GET` | `/chats/{id}/messages` | Full turn history (`MessageRead[]`, ordered). |
| `POST` | `/chats/{id}/messages` | Persist a message **without** streaming a reply. |

### 3.3 Stream a reply — `POST /chats/{id}/messages/stream`

Request body `MessageCreate`:

```json
{ "content": "Say hello in one sentence.", "role": "user" }
```

Behavior: persists the user message → opens the engine stream → streams deltas →
persists the assistant reply before closing. After completion,
`GET /chats/{id}/messages` returns the full turn.

**SSE events** (in order):

| Event | `data` payload | Meaning |
|---|---|---|
| `message.accepted` | `{ chat_id, message_id, model_id }` | User message stored; model resolved; generation started. |
| `message.delta` | `{ message_id, index, delta }` | One text chunk. Concatenate `delta` in `index` order to build the reply. |
| `message.completed` | `{ message_id, assistant_message_id, content }` | Final full text; assistant reply persisted. Terminal. |
| `message.error` | `{ message_id, code, message, retryable }` | Provider failure **or** report-context retrieval failure (report-linked chats only). Terminal. |

`event_id` format is `"{user_message_id}:{index}"`.

**Error codes** (`code` on `message.error`) — all provider-neutral, keyed off the
selected provider's display name:

| `code` | `retryable` | Frontend hint |
|---|---|---|
| `provider_credential_invalid` | false | Key invalid/expired — prompt user to re-enter. |
| `provider_permission_denied` | false | Key lacks permission for this request. |
| `provider_credits_exhausted` | false | Account out of credits. |
| `provider_rate_limited` | true | Back off and retry. |
| `provider_unavailable` | true | Transient; retry. |
| `provider_capacity_unavailable` | true | Transient; retry. |
| `provider_invalid_json_response` | true | Transient; retry. |
| `report_context_unavailable` | true | **Report-linked chats only.** The vector store backing the attached report was unreachable, so the chat was failed rather than answered without the report. `message` is a generic "system experiencing a lot of load, please try again later." Back off and retry. |

### 3.4 What context the engine receives

`ChatAgentInput` has exactly two fields — `context` and `message`:

- `message` = the just-sent user message content.
- `context` = **prior chat turns**, and — for a report-linked chat — **retrieved
  report passages** prepended ahead of them. Both are packed into the single
  `context` string (`build_stream` in `api/services/chat_stream.py`); the engine
  budgeter trims to fit the model window. The report block is labelled
  `Attached report context:` so the model can tell it from conversation history.

For a chat **without** a `report_id`, `context` is prior turns only, and the vector
store is never consulted.

### 3.5 Report-as-context (report-linked chats)

**Attaching `report_id` to a chat injects that report into the model context.** Each
reply then has both the running conversation and the report.

How it works:

- When a research run finishes, the finalized report is embedded into a
  tenant-scoped vector store, keyed by `user_id` **and** `report_id`.
- On every `POST /chats/{id}/messages/stream` for a report-linked chat, the backend
  runs a vector search scoped to that user + that report, using the new user message
  as the query, and prepends the top matching passages to `context` (§3.4).
- Isolation is enforced in the store: a chat only ever retrieves *its* report's
  passages — never another report's, never another user's.

Caveats the frontend should know:

- **Timing.** Only a *finalized* report is embedded. A report still being produced
  (research running) has nothing to retrieve yet, so early replies won't reflect it.
  A report created purely via manual `POST /reports/{id}/versions` (no research run)
  is **not** auto-embedded and won't be retrievable.
- **Failure.** If the vector store is unreachable, the chat turn is **failed**, not
  answered without the report — the stream ends with a terminal `message.error`
  carrying `code: "report_context_unavailable"` (`retryable: true`) and a generic
  load message. Surface it as a transient "try again" state; do not treat it as a
  normal answer. (§3.3 error table.)

### 3.6 Summaries (optional)

- `GET /chats/{id}/summaries` / `POST /chats/{id}/summaries` — durable
  chat-summary checkpoints for long conversations. Not required for basic chat.

---

## 4. Research mode — durable background job

Research is a long-running (up to 4h) LangGraph job. `POST /research/runs` **queues**
it and returns `202` immediately; a separate ARQ worker executes it. Progress is
observed by replaying durable events over SSE. The final report is stored separately
and read through the **Reports** endpoints.

**Infra required server-side:** `SINGULARITY_RESEARCH_WORKER_ENABLED=1`, a running
Redis, and a running ARQ worker (`arq api.research_worker.WorkerSettings`). Real web
tools additionally need a deployed Modal function (`SINGULARITY_MODAL_ENABLED=1`).
Without the worker, `POST /research/runs` returns **`503`**.

### 4.1 Create a run — `POST /research/runs`

Body `ResearchRunCreate`:

```json
{
  "query": "What is retrieval-augmented generation?",  // REQUIRED
  "title": "RAG overview",                             // optional
  "report_id": "rep_...",                              // optional; attach to existing report
  "provider_credential_id": "cred_...",                // BYOK key for the run
  "model_id": "openai/gpt-oss-20b",                    // optional
  "strength": 2,                                       // 1..3, default 2 (depth/cost)
  "audience": "practitioner",                          // default
  "output_language": "en",                             // default
  "test_mode": false                                   // see §4.5
}
```

Response `202` (`ResearchRunRead`):

```json
{
  "id": "run_...",
  "user_id": "...",
  "report_id": "rep_..." | null,   // where the finished report lands (see §4.4)
  "query": "…",
  "status": "queued",              // queued | running | completed | failed | cancelled
  "engine_version": null,
  "started_at": null, "finished_at": null,
  "error_message": null,
  "run_data": {}
}
```

> Always confirm the response has a non-empty `id`. A `503`/`403` body has no `id`;
> streaming `/research/runs//events` afterward yields `404 "Research run not found"`.

### 4.2 Run CRUD

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/research/runs` | List the user's runs (`ResearchRunRead[]`). |
| `GET` | `/research/runs/{id}` | Poll one run (status + `report_id`). |
| `POST` | `/research/runs/{id}/cancel` | Request cancellation. |

### 4.3 Stream progress — `GET /research/runs/{id}/events`

Long-lived SSE. **Replays** all durable events from the start, then stays open,
emitting heartbeats until a terminal event. Supports reconnection via the
`Last-Event-ID` request header (pass the last `id:` you saw; the server resumes after
it). `id:` values are monotonic integer sequence numbers.

**Lifecycle events:**

| Event | `data` (key fields) | Notes |
|---|---|---|
| `research.queued` | `{ run_id, status }` | Accepted into the queue. |
| `research.running` | `{ run_id, status }` | Worker picked it up. |
| `research.progress` | `{ run_id, phase, status, message, … }` | Granular pipeline progress (see below). |
| `research.phase` | `{ run_id, node, details, cycle }` | Graph node boundary crossed. |
| `research.heartbeat` | `{ run_id, status }` | Keep-alive; **no `id:`**. Ignore for UI, or show "working…". |
| `research.completed` | `{ run_id, status }` | Success. Terminal — fetch the report (§4.4). |
| `research.failed` | `{ run_id, status, error, reason? }` | Failure. Terminal. `reason: "infrastructure_unavailable"` = transient backend issue. |
| `research.cancelled` | `{ run_id, status }` | Cancelled. Terminal. |

**`research.progress` `phase` / `status` values** observed in a run — useful for a
progress UI:

- `phase: "planning"` → `started`/`completed` (`"Clarifying research objective"`,
  `"Generating independent research angles"`, `"Building bounded research plan"`).
- `phase: "researching"` → `started`, `node_started`, `tool_dispatched`,
  `tool_completed`, `node_completed`, `completed`. Tool events carry
  `tool_name` (`web_search` / `web_fetch`), `elapsed_seconds`, `source_count`.
- `phase: "writing"` → `started`/`completed` (`"Writing sourced research report"`).

A frontend can drive a step indicator directly off `phase` + `status`, and a live
activity log off `message`.

### 4.4 Read the finished report

On `research.completed`, the report content lives on the run's `report_id`, read via
the **Reports** endpoints:

1. `GET /research/runs/{id}` → take `report_id`.
2. Read the content, two options:

| Method | Path | Returns |
|---|---|---|
| `GET` | `/reports/{report_id}/stream` | SSE replay of the markdown (`report.started` → `report.delta` → `report.completed`). Best for a streaming render. Emits a single `report.pending` if no version exists yet. |
| `GET` | `/reports/{report_id}/versions` | `ReportVersionRead[]`; take the last `id` for the latest version. |
| `GET` | `/reports/{report_id}/versions/{version_id}/content` | Raw markdown (`text/markdown`). Best for one-shot read. |

**Report SSE events** (`/reports/{id}/stream`):

| Event | `data` | Notes |
|---|---|---|
| `report.started` | `{ report_id, title, version_number }` | |
| `report.pending` | `{ report_id, status }` | No version yet (research still running). Terminal for this stream. |
| `report.delta` | `{ report_id, index, delta }` | Markdown chunk. |
| `report.completed` | `{ report_id, content }` | Full markdown. Terminal. |

Other report endpoints: `GET/POST /reports`, `GET /reports/{id}`,
`POST /reports/{id}/versions`.

> **Report embedding on completion.** When a run finalizes, the report is both
> stored as a version **and** embedded into the vector store so a report-linked
> chat can ground on it (§3.5). This embedding is part of finalization: if the
> vector store is unreachable, the run is failed (`research.failed`,
> `reason: "infrastructure_unavailable"`) and the report is **not** marked
> `ready`, rather than completing a report its chats couldn't retrieve. Retry the
> run.

### 4.5 `test_mode` (smoke test only)

Forces a minimal run — **one node, one `web_search`, one `web_fetch`, no QA cycle** —
to prove wiring cheaply. Requires **both** the server flag
`SINGULARITY_RESEARCH_TEST_MODE=1` **and** `"test_mode": true` in the body. If the
body flag is sent while the server flag is off, the run is rejected `403` (never
silently upgraded). When active, the minimal profile applies regardless of `strength`.
Not for production traffic.

---

## 5. Chat vs Research — at a glance

| | **Chat** | **Research** |
|---|---|---|
| Trigger | `POST /chats/{id}/messages/stream` | `POST /research/runs` |
| Execution | Synchronous, in-request | Async background job (ARQ + Redis worker) |
| Initial response | `200` SSE stream | `202` + run id |
| Duration | Seconds | Minutes → hours |
| Progress | `message.*` deltas | `GET /research/runs/{id}/events` (`research.*`) |
| Result location | In the stream + persisted messages | Stored report (`report_id` → Reports API) |
| Reconnect/replay | No (resend) | Yes (`Last-Event-ID`) |
| Infra needed | Server only | Server + Redis + worker (+ Modal for tools) |
| BYOK credential | Required on the chat | Passed per run |

---

## 6. Integration checklist

- [ ] Auth header on every request (`Authorization: Bearer` in prod).
- [ ] Create/select a BYOK credential before Chat or Research; surface
      `provider_credential_invalid` errors as "re-enter key".
- [ ] Chat: ensure `provider_credential_id` is set or handle the `422`.
- [ ] Chat: concatenate `message.delta` by `index`; treat `message.completed`/`message.error` as terminal.
- [ ] Report-linked chat: the assistant *does* read the attached report once it is
      finalized (§3.5). Handle `message.error` `code: "report_context_unavailable"`
      as a transient "try again", not an answer.
- [ ] Research: verify a non-empty `id` before streaming events; handle `503` (worker off).
- [ ] Research: ignore `research.heartbeat` for UI; drive progress off `research.progress`.
- [ ] Research: on `research.completed`, fetch report via `report_id` → Reports API.
- [ ] Use `Last-Event-ID` to resume the research event stream after a dropped connection.
