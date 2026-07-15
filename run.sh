#!/usr/bin/env bash
#
# run.sh — start all Singularity services locally with one command.
#
# Brings up the infrastructure containers (Postgres, Redis, Qdrant) via
# Docker Compose, then runs the application processes locally:
#   - API server        (uvicorn, :8000)
#   - Research worker    (arq)
#   - Frontend           (next dev, :3000)
#
# All application logs are streamed to ./logs/ and the processes are torn
# down together on Ctrl-C.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

LOG_DIR="$ROOT/logs"
mkdir -p "$LOG_DIR"

# ---------------------------------------------------------------------------
# Load a KEY=VALUE .env file into the environment.
#
# Pydantic Settings and Next.js read their .env files on their own, but some
# code paths use raw os.getenv (e.g. SINGULARITY_MODAL_ENABLED in
# api/services/chat_stream.py), which only sees variables present in the
# process environment. Exporting the file here keeps every path consistent.
# Existing environment values win, so an explicit override on the command line
# (or an already-loaded parent file) is respected.
# ---------------------------------------------------------------------------
load_env_file() {
  local file="$1"
  [[ -f "$file" ]] || return 0
  echo "==> Loading environment from ${file#$ROOT/}..."
  local line key
  while IFS= read -r line || [[ -n "$line" ]]; do
    # Skip blanks and comments; only accept KEY=VALUE lines.
    [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue
    [[ "$line" != *=* ]] && continue
    key="${line%%=*}"
    key="$(printf '%s' "$key" | tr -d '[:space:]')"
    # Don't clobber a value already set in the environment.
    if [[ -z "${!key:-}" ]]; then
      export "$line"
    fi
  done < "$file"
}

load_env_file "$ROOT/.env"

# ---------------------------------------------------------------------------
# Resolve the Python environment (prefer the project virtualenv).
# ---------------------------------------------------------------------------
if [[ -x "$ROOT/.venv/bin/python" ]]; then
  PY="$ROOT/.venv/bin/python"
  BIN="$ROOT/.venv/bin"
else
  PY="$(command -v python3)"
  BIN="$(dirname "$PY")"
fi

# Pick the docker compose invocation available on this machine.
if docker compose version >/dev/null 2>&1; then
  DC="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
  DC="docker-compose"
else
  echo "error: docker compose is required to start the infrastructure services" >&2
  exit 1
fi

# ---------------------------------------------------------------------------
# Decide which infrastructure to start based on the database backend.
# SINGULARITY_USE_SQLITE=true (local dev) needs only Redis; otherwise the
# backend targets Postgres, so bring up Postgres and Qdrant too.
# The value is read from the environment first, falling back to .env.
# ---------------------------------------------------------------------------
use_sqlite="${SINGULARITY_USE_SQLITE:-}"
if [[ -z "$use_sqlite" && -f "$ROOT/.env" ]]; then
  use_sqlite="$(grep -E '^\s*SINGULARITY_USE_SQLITE\s*=' "$ROOT/.env" | tail -1 | cut -d= -f2- | tr -d '[:space:]' || true)"
fi

case "$(printf '%s' "$use_sqlite" | tr '[:upper:]' '[:lower:]')" in
  1 | true | yes | on)
    # Local dev: SQLite for the relational store, but the research worker still
    # ingests reports into Qdrant, so bring up the local Qdrant container and
    # point the app at it (unless QDRANT_URL is already set, e.g. to point at a
    # cloud instance). Prod leaves QDRANT_URL set in the environment/.env.
    INFRA_SERVICES=(redis qdrant)
    DB_BACKEND="SQLite (local)"
    : "${QDRANT_URL:=http://localhost:6333}"
    export QDRANT_URL
    ;;
  *)
    INFRA_SERVICES=(postgres redis qdrant)
    DB_BACKEND="PostgreSQL"
    ;;
esac

# ---------------------------------------------------------------------------
# Preflight: refuse to start when an app port is already taken. A stale
# frontend/API from a previous session otherwise makes the new process exit
# immediately, and the watchdog below then tears everything down — which looks
# like the backend "stopping on its own".
# ---------------------------------------------------------------------------
for port in 8000 3000; do
  holder="$(lsof -nP -iTCP:$port -sTCP:LISTEN -t 2>/dev/null | head -1 || true)"
  if [[ -n "$holder" ]]; then
    echo "error: port $port is already in use by:" >&2
    ps -p "$holder" -o pid,etime,command | tail -1 >&2
    echo "Stop it first (kill $holder), then rerun ./run.sh." >&2
    exit 1
  fi
done

PIDS=()

cleanup() {
  echo
  echo "==> Shutting down application processes..."
  for pid in "${PIDS[@]:-}"; do
    if [[ -n "${pid:-}" ]] && kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null || true
    fi
  done
  wait 2>/dev/null || true
  echo "==> Stopping infrastructure containers..."
  $DC stop "${INFRA_SERVICES[@]}" >/dev/null 2>&1 || true
  echo "==> Done."
}
trap cleanup INT TERM EXIT

# ---------------------------------------------------------------------------
# 1. Infrastructure
# ---------------------------------------------------------------------------
echo "==> Database backend: $DB_BACKEND"
echo "==> Starting infrastructure (${INFRA_SERVICES[*]})..."
$DC up -d "${INFRA_SERVICES[@]}"

echo "==> Waiting for services to be healthy..."
for _ in $(seq 1 30); do
  all_healthy=1
  for svc in "${INFRA_SERVICES[@]}"; do
    # Only services with a healthcheck report a health status; treat an empty
    # status (e.g. qdrant, which has none) as ready.
    health=$($DC ps "$svc" --format '{{.Health}}' 2>/dev/null || echo "")
    if [[ -n "$health" && "$health" != "healthy" ]]; then
      all_healthy=0
    fi
  done
  [[ "$all_healthy" == 1 ]] && break
  sleep 1
done

# ---------------------------------------------------------------------------
# 2. Database migrations
# ---------------------------------------------------------------------------
echo "==> Applying database migrations (alembic upgrade head)..."
"$BIN/alembic" upgrade head

# ---------------------------------------------------------------------------
# 3. Application processes
# ---------------------------------------------------------------------------
NAMES=()

echo "==> Starting API server (:8000)..."
"$BIN/uvicorn" api.main:app --host 0.0.0.0 --port 8000 --reload \
  >"$LOG_DIR/api.log" 2>&1 &
PIDS+=($!)
NAMES+=("API server (logs/api.log)")

echo "==> Starting research worker (arq)..."
"$BIN/arq" api.research_worker.WorkerSettings \
  >"$LOG_DIR/worker.log" 2>&1 &
PIDS+=($!)
NAMES+=("research worker (logs/worker.log)")

echo "==> Starting frontend (:3000)..."
(
  # Load the frontend's own env explicitly. Next.js also auto-loads
  # frontend/.env, but exporting it here makes the values available to the
  # process regardless of how it is launched. Root .env values already
  # exported above are not overwritten (existing values win).
  load_env_file "$ROOT/frontend/.env"
  cd "$ROOT/frontend"
  [[ -d node_modules ]] || npm install
  npm run dev
) >"$LOG_DIR/frontend.log" 2>&1 &
PIDS+=($!)
NAMES+=("frontend (logs/frontend.log)")

echo
echo "All services started:"
echo "  API       -> http://localhost:8000   (logs: logs/api.log)"
echo "  Worker    -> arq research worker       (logs: logs/worker.log)"
echo "  Frontend  -> http://localhost:3000     (logs: logs/frontend.log)"
echo
echo "Press Ctrl-C to stop everything."

# Wait on the application processes; exit (and trigger cleanup) when any dies.
# ``wait -n`` is bash 4+, but macOS ships bash 3.2, so poll the PIDs instead.
while true; do
  for i in "${!PIDS[@]}"; do
    if ! kill -0 "${PIDS[$i]}" 2>/dev/null; then
      echo "==> ${NAMES[$i]} exited; shutting everything down. Check its log for the cause."
      exit 1
    fi
  done
  sleep 2
done
