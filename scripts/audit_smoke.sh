#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

log() {
  printf '[audit_smoke] %s\n' "$1"
}

COMPOSE_CMD=${COMPOSE_CMD:-docker compose}

log "Ensuring core telemetry stack is running (OPA, orchestrator, audit collector, NATS)…"
$COMPOSE_CMD up -d opa orchestrator audit_collector nats spawn_service >/dev/null

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

log "Waiting for audit file '${AUDIT_FILE}' to appear (timeout ${FILE_TIMEOUT}s)…"
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
MATCH_COUNT=0
while [[ $SECONDS -lt $deadline ]]; do
  MATCH_COUNT=$(jq -c --arg sid "$SCENARIO_ID" \
    'select(.event == "scenario.created" and (.payload.scenario_id == $sid))' \
    "$AUDIT_FILE" | wc -l | tr -d ' ')
  if [[ "$MATCH_COUNT" -gt 0 ]]; then
    break
  fi
  sleep 1
done

if [[ "$MATCH_COUNT" -eq 0 ]]; then
  log "ERROR: No 'scenario.created' telemetry found for scenario ${SCENARIO_ID} within timeout."
  exit 1
fi

log "Found $MATCH_COUNT 'scenario.created' event(s) in '$AUDIT_FILE'."

if [[ -x "./scripts/audit_report.sh" ]]; then
  log "Summary:"
  if ! ./scripts/audit_report.sh; then
    log "(audit_report failed; ignoring for now)"
  fi
fi

log "OK."
