#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

OPA_URL="${OPA_URL:-http://localhost:8181}"

echo "[opa_debug] docker ps:"
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'

echo
echo "[opa_debug] curl -v ${OPA_URL}/v1/data/system/version"
set +e
curl -v "${OPA_URL}/v1/data/system/version"
RC=$?
set -e

echo
echo "[opa_debug] curl exit code: ${RC}"

echo
echo "[opa_debug] last 40 lines of opa logs (if container exists):"
if docker ps -a --format '{{.Names}}' | grep -q 'opa'; then
  docker logs "$(docker ps -a --format '{{.Names}}' | grep 'opa' | head -n1)" | tail -n 40 || true
else
  echo "[opa_debug] no opa container found."
fi
