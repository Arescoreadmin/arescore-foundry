#!/usr/bin/env bash
set -euo pipefail

# Always run from repo root
cd "$(dirname "$0")/.."

# Use the main compose file + OPA overlay so services have images/builds
COMPOSE_FILES="-f compose.yml -f infra/compose.opa.yml"

echo "[opa_up] Bringing up stack with: docker compose ${COMPOSE_FILES} up -d"
docker compose ${COMPOSE_FILES} up -d
