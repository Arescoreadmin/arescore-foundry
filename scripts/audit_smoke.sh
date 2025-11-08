#!/usr/bin/env bash
set -euo pipefail

log() {
  printf '[audit_smoke] %s\n' "$1"
}

log "Ensuring stack is up (orchestrator + spawn + OPA)…"
./scripts/opa_up.sh >/dev/null

AUDIT_FILE="${FOUNDRY_TELEMETRY_PATH:-audits/foundry-events.jsonl}"
AUDIT_TIMEOUT="${AUDIT_TIMEOUT:-60}"
FILE_TIMEOUT="${AUDIT_FILE_TIMEOUT:-15}"

if ! command -v jq >/dev/null 2>&1; then
  log "ERROR: jq is required to inspect audit telemetry."
  exit 1
fi

log "Spawning scenario via single_site_scenario_create.sh…"
TMP_LOG="$(mktemp -t audit_smoke_scenario_XXXX.log)"
trap 'rm -f "$TMP_LOG"' EXIT

./scripts/single_site_scenario_create.sh | tee "$TMP_LOG"

SCENARIO_ID="$(grep -E '^ID=' "$TMP_LOG" | sed 's/^ID=//')"
if [[ -z "${SCENARIO_ID:-}" ]]; then
  log "ERROR: Failed to determine scenario ID from single_site_scenario_create.sh output."
  exit 1
fi
log "Scenario ID: ${SCENARIO_ID}"

deadline=$((SECONDS + FILE_TIMEOUT))
while [[ $SECONDS -lt $deadline ]]; do
  if [[ -f "$AUDIT_FILE" ]]; then
    break
  fi
  sleep 1
done

if [[ ! -f "$AUDIT_FILE" ]]; then
  log "ERROR: audit file '$AUDIT_FILE' does not exist."
  exit 1
fi

log "Waiting up to ${AUDIT_TIMEOUT}s for telemetry matching scenario ${SCENARIO_ID}…"
deadline=$((SECONDS + AUDIT_TIMEOUT))
found=0
while [[ $SECONDS -lt $deadline ]]; do
  if jq -e --arg sid "$SCENARIO_ID" \
    'select(.event == "scenario.created" and (.payload.scenario_id == $sid))' \
    "$AUDIT_FILE" >/dev/null 2>&1; then
    found=1
    break
  fi
  sleep 1
done

if [[ $found -eq 0 ]]; then
  log "ERROR: No 'scenario.created' telemetry found for scenario ${SCENARIO_ID} within timeout."
  exit 1
fi

MATCH_COUNT="$(jq -r --arg sid "$SCENARIO_ID" \
  'select(.event == "scenario.created" and (.payload.scenario_id == $sid)) | 1' \
  "$AUDIT_FILE" 2>/dev/null | wc -l | awk '{print $1}')"
log "Confirmed ${MATCH_COUNT} 'scenario.created' event(s) for scenario ${SCENARIO_ID}."

# Optional: pretty summary
if [[ -x "./scripts/audit_report.sh" ]]; then
  echo "[audit_smoke] Summary:"
  ./scripts/audit_report.sh || echo "[audit_smoke] (audit_report failed; ignoring for now)"
fi

echo "[audit_smoke] OK."

