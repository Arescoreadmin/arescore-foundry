#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo ">>> Tearing down single-site stack…"

docker compose \
  -f compose.yml \
  -f compose.federated.yml \
  -f infra/compose.opa.yml \
  -f compose.single.yml \
  down -v || true

echo "Single-site stack is DOWN."
