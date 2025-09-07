#!/usr/bin/env bash
set -euo pipefail
SUFFIX="${1:-clone}"
export COMPOSE_PROJECT_NAME="arescore_${SUFFIX}"
export STACK_SUFFIX="${SUFFIX}"

docker compose -f infra/docker-compose.yml -f infra/docker-compose.override.yml up -d

echo "Cloned stack up: ${COMPOSE_PROJECT_NAME}"