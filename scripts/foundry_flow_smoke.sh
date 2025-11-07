#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

ORCH_URL="${ORCH_URL:-http://localhost:8080}"

echo "[foundry_flow_smoke] Orchestrator health…"
curl -sf "${ORCH_URL}/health" || { echo "[foundry_flow_smoke] orchestrator /health failed"; exit 1; }

echo
echo "[foundry_flow_smoke] Spawn netplus scenario via existing script…"
OUT=$(./scripts/single_site_scenario_create.sh netplus)

# Show whatever the script prints (for debugging)
printf '%s\n' "$OUT"

# Extract ID=bla-bla-bla from the output
SCENARIO_ID=$(printf '%s\n' "$OUT" | awk -F= '/^ID=/{print $2}' | tr -d '\r')

if [ -z "${SCENARIO_ID}" ]; then
  echo "[foundry_flow_smoke] Could not extract scenario ID from single_site_scenario_create.sh output."
  exit 1
fi

echo
echo "[foundry_flow_smoke] Parsed scenario id: ${SCENARIO_ID}"

echo
echo "[foundry_flow_smoke] Fetch scenario by id from orchestrator (/api/scenarios/{scenario_id})…"
curl -s "${ORCH_URL}/api/scenarios/${SCENARIO_ID}" | jq . || {
  echo "[foundry_flow_smoke] GET /api/scenarios/${SCENARIO_ID} failed or returned non-JSON."
  exit 1
}

echo
echo "[foundry_flow_smoke] Done."
