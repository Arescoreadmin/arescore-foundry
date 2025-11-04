#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

COMPOSE_FILES="-f compose.yml -f compose.federated.yml -f infra/compose.opa.yml -f compose.single.yml"

echo "==> Bringing down single-site stack"
docker compose $COMPOSE_FILES down -v

echo "==> Remaining containers (should be none for foundry stack):"
docker ps --filter name=arescore-foundry --format "table {{.Names}}\t{{.Status}}"
