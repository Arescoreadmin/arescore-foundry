#!/usr/bin/env bash
set -euo pipefail

log() {
  printf '[audit_smoke] %s\n' "$1"
}

log "Ensuring stack is up (orchestrator + spawn + OPA)…"
./scripts/opa_up.sh >/dev/null

AUDIT_FILE="${FOUNDRY_TELEMETRY_PATH:-audits/foundry-events.jsonl}"

log "Spawning scenario via single_site_scenario_create.sh…"
TMP_LOG="$(mktemp -t audit_smoke_scenario_XXXX.log)"
trap 'rm -f "$TMP_LOG"' EXIT

./scripts/single_site_scenario_create.sh | tee "$TMP_LOG"

SCENARIO_ID="$(grep -E '^ID=' "$TMP_LOG" | sed 's/^ID=//')"
log "Scenario ID: ${SCENARIO_ID:-<unknown>} (for reference)"

sleep 2

if [ ! -f "$AUDIT_FILE" ]; then
  log "ERROR: audit file '$AUDIT_FILE' does not exist."
  exit 1
fi

MATCH_COUNT="$(grep -c '"event":"scenario.created"' "$AUDIT_FILE" || true)"
log "Found ${MATCH_COUNT} 'scenario.created' event(s) in '$AUDIT_FILE'."

if [ "${MATCH_COUNT}" -lt 1 ]; then
  log "ERROR: Expected at least one 'scenario.created' event."
  exit 1
fi

log "OK."
