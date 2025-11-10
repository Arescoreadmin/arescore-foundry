#!/usr/bin/env bash
set -euo pipefail

log() {
  printf '[audit_smoke] %s\n' "$1"
}

log "Ensuring stack is up (orchestrator + spawn + OPA)…"
./scripts/opa_up.sh >/dev/null

# Where telemetry writes JSONL events. This matches telemetry.py default / compose wiring.
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

SCENARIO_ID="$(
  sed -n 's/^ID=//p' "$TMP_LOG" \
    | head -n 1 \
    | tr -d '[:space:]'
)"

if [[ -z "${SCENARIO_ID:-}" ]]; then
  log "ERROR: Failed to determine scenario ID from single_site_scenario_create.sh output."
  exit 1
fi

log "Scenario ID: ${SCENARIO_ID}"

# Wait for audit file to appear
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
MATCH_COUNT=0

while [[ $SECONDS -lt $deadline ]]; do
  MATCH_COUNT="$(
    jq -r --arg sid "$SCENARIO_ID" \
       'select(.event == "scenario.created" and .payload.scenario_id == $sid) | 1' \
       "$AUDIT_FILE" 2>/dev/null \
      | wc -l | awk '{print $1}'
  )"

  if [[ "$MATCH_COUNT" -gt 0 ]]; then
    found=1
    break
  fi

  sleep 1
done

if [[ $found -eq 0 ]]; then
  log "ERROR: No 'scenario.created' telemetry found for scenario ${SCENARIO_ID} within timeout."

  # Dump a quick summary to help debugging
  if [[ -x "./scripts/audit_report.sh" ]]; then
    ./scripts/audit_report.sh || log "(audit_report failed; ignoring for now)"
  fi

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
  log "Summary:"
  ./scripts/audit_report.sh || log "(audit_report failed; ignoring for now)"
fi

log "OK."
