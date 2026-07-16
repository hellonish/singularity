#!/usr/bin/env bash
#
# Backend deploy for the live EC2 box.
#
# Run this ON EC2, from anywhere, after you have `git push`ed from your Mac:
#
#     ./deploy/deploy.sh              # plain code change (no migration)
#     ./deploy/deploy.sh --migrate    # run Alembic migrations this release
#     ./deploy/deploy.sh -m           # short form
#
# It pulls main, rebuilds the app image, optionally migrates, then recreates
# api + worker together (leaving redis and caddy running) and verifies health.
#
set -euo pipefail

# --- config -----------------------------------------------------------------
REPO_DIR="/opt/singularity"
COMPOSE_FILE="docker-compose.prod.yml"
ENV_FILE=".env.production"
HEALTH_URL="https://singularity-api.hellonish.dev/health"
STORAGE_HEALTH_URL="https://singularity-api.hellonish.dev/storage/health"

# --- args -------------------------------------------------------------------
RUN_MIGRATE=false
for arg in "$@"; do
  case "$arg" in
    -m|--migrate) RUN_MIGRATE=true ;;
    -h|--help)
      grep '^#' "$0" | sed 's/^# \{0,1\}//' | head -n 13
      exit 0
      ;;
    *)
      echo "Unknown argument: $arg (use --migrate or --help)" >&2
      exit 2
      ;;
  esac
done

# helper so we don't repeat the long compose invocation
dc() { docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" "$@"; }

log() { printf '\n\033[1;36m==> %s\033[0m\n' "$*"; }

cd "$REPO_DIR"

# --- pull -------------------------------------------------------------------
log "Pulling latest main"
git pull origin main
SHA="$(git rev-parse --short HEAD)"
log "Now at commit ${SHA}"

# --- build ------------------------------------------------------------------
log "Building api image"
dc build api

# --- migrate (optional) -----------------------------------------------------
if [ "$RUN_MIGRATE" = true ]; then
  # LangGraph checkpoint setup includes DDL. Stop old workers before it runs so
  # a long-lived research transaction cannot hold a lock until Supabase cancels
  # the migration for exceeding statement_timeout.
  log "Stopping api + worker before migrations"
  dc stop api worker
  log "Running Alembic migrations"
  dc run --rm migrate
else
  log "Skipping migrations (pass --migrate to run them)"
fi

# --- recreate api + worker together ----------------------------------------
# --no-deps: don't let compose re-run the `migrate` dependency on recreate.
log "Recreating api + worker"
dc up -d --no-deps --force-recreate api worker

# --- verify -----------------------------------------------------------------
log "Verifying health endpoints"
curl -fsS "$HEALTH_URL" && echo
curl -fsS "$STORAGE_HEALTH_URL" && echo

log "Service status"
dc ps

log "Deploy of ${SHA} complete. Recent logs:"
dc logs --tail=40 api worker
