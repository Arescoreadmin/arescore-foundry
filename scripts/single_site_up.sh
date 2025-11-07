#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo ">>> Bringing up single-site stack…"

docker compose \
  -f compose.yml \
  -f compose.federated.yml \
  -f infra/compose.opa.yml \
  -f compose.single.yml \
  up -d --build

echo ">>> Waiting a few seconds for services to settle…"
sleep 8

echo ">>> Health checks"
curl -fsS http://localhost:8080/health > /dev/null
curl -fsS http://localhost:9092/health > /dev/null
curl -fsS http://localhost:9093/health > /dev/null
curl -fsS http://localhost:9094/health > /dev/null

echo ">>> Creating demo scenario via orchestrator…"
SCENARIO_ID="$(
  curl -fsS -X POST http://localhost:8080/api/scenarios \
    -H 'Content-Type: application/json' \
    -d '{
      "name": "netplus-demo",
      "template": "netplus",
      "description": "Single-site demo scenario"
    }' \
  | jq -r '.id'
)"

echo ">>> Demo scenario ID: ${SCENARIO_ID}"

echo ">>> Fetching scenario back…"
curl -fsS "http://localhost:8080/api/scenarios/${SCENARIO_ID}" | jq .

echo
echo "Single-site stack is UP."
echo "Swagger:  http://localhost:8080/docs"
