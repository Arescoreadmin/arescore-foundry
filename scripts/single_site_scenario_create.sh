#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   ./scripts/single_site_scenario_create.sh [name] [template] [description]
#
# Defaults:
#   name       = netplus-demo
#   template   = netplus
#   desc       = Single-site demo scenario

NAME="${1:-netplus-demo}"
TEMPLATE="${2:-netplus}"
DESC="${3:-Single-site demo scenario}"

ORCH_URL="${ORCHESTRATOR_URL:-http://localhost:8080}"

echo ">>> Creating scenario:"
echo "    name:      ${NAME}"
echo "    template:  ${TEMPLATE}"
echo "    desc:      ${DESC}"

if ! command -v jq >/dev/null 2>&1; then
  echo "[single_site_scenario_create] ERROR: jq is required."
  exit 1
fi

payload="$(jq -n \
  --arg name "$NAME" \
  --arg tmpl "$TEMPLATE" \
  --arg desc "$DESC" \
  '{name: $name, template: $tmpl, description: $desc}')"

SCENARIO_ID="$(
  curl -fsS -X POST "${ORCH_URL}/api/scenarios" \
    -H 'Content-Type: application/json' \
    -d "$payload" \
  | jq -r '.id'
)"

echo ">>> Scenario created"
echo "ID=${SCENARIO_ID}"
