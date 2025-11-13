#!/usr/bin/env bash
set -euo pipefail

log() {
  printf '[foundry_flow_smoke] %s\n' "$1"
}

ORCH_URL="${ORCHESTRATOR_URL:-http://localhost:8080}"

log "Orchestrator health…"

body="$(curl -fsS "${ORCH_URL}/health" || true)"

if [[ -z "$body" ]]; then
  log "orchestrator /health failed (empty response)"
  exit 1
fi

if ! echo "$body" | grep -q '"ok":true'; then
  log "orchestrator /health failed, got: $body"
  exit 1
fi

log "orchestrator /health OK"
