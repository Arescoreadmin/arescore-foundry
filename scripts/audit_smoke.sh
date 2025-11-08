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

# existing check already sets AUDIT_FILE and MATCH_COUNT
if [[ "$MATCH_COUNT" -eq 0 ]]; then
  echo "[audit_smoke] ERROR: no 'scenario.created' events found in '$AUDIT_FILE'."
  exit 1
fi

echo "[audit_smoke] Found $MATCH_COUNT 'scenario.created' event(s) in '$AUDIT_FILE'."

# Optional: pretty summary
if [[ -x "./scripts/audit_report.sh" ]]; then
  echo "[audit_smoke] Summary:"
  ./scripts/audit_report.sh || echo "[audit_smoke] (audit_report failed; ignoring for now)"
fi

echo "[audit_smoke] OK."

