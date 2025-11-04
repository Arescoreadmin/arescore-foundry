#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "==> Running OPA unit tests (policies)"
docker run --rm \
  -v "$PWD/policies:/policies:ro" \
  openpolicyagent/opa:1.10.0 test -v /policies

echo "==> Bringing up single-site stack (no spawn_service)"
COMPOSE_FILES="-f compose.yml -f compose.federated.yml -f infra/compose.opa.yml -f compose.single.yml"

docker compose $COMPOSE_FILES up -d --build

echo "==> Current containers:"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo "==> Running overlay smoke (reuse existing script)"
bash scripts/smoke_overlay.sh || {
  echo "!! smoke_overlay failed; see logs above"
  exit 1
}

echo "==> Single-site stack is up and healthy."
