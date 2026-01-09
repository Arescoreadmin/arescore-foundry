#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo ">>> Docker services:"
docker ps --filter "name=arescore-foundry" \
  --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo
echo ">>> Orchestrator health"
curl -fsS http://localhost:8080/health | jq .

echo
echo ">>> FL coordinator health"
curl -fsS http://localhost:9092/health | jq .

echo
echo ">>> Consent registry health"
curl -fsS http://localhost:9093/health | jq .

echo
echo ">>> Evidence bundler health"
curl -fsS http://localhost:9094/health | jq .

echo
echo ">>> OPA root endpoint"
curl -fsS http://localhost:8181/ || echo "(OPA reachable but non-JSON)"

echo
echo ">>> Spawn service quick checks (inside container)"
SPAWN_CID="$(docker ps --filter name=arescore-foundry-spawn_service-1 --format '{{.ID}}' || true)"

if [ -z "$SPAWN_CID" ]; then
  echo "spawn_service container not found (maybe single-site overlay only?). Skipping."
else
  docker exec "$SPAWN_CID" sh -c '
    echo "  - /templates contents:"
    ls /templates || echo "    (no templates dir)"
  '
fi

echo
echo "Health check complete."
