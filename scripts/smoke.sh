#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

echo "==> Up (build)"; docker compose -f infra/docker-compose.yml up -d --build

wait_url() {
  local url="$1"
  echo "Waiting for $url"
  for i in {1..60}; do
    if curl -fsS "$url" >/dev/null; then
      echo "OK: $url"; return 0
    fi
    sleep 2
  done
  echo "TIMEOUT: $url"; return 1
}

wait_url http://localhost:3000/ready
wait_url http://localhost:3000/api/ready
wait_url http://localhost:8000/health
wait_url http://localhost:8080/health

echo "==> Assertions"
test "$(curl -fsS http://localhost:3000/ready)" = '{"ready":true}'
test "$(curl -fsS http://localhost:3000/api/ready | sed 's/ //g' | grep -o '"ready":true')" = '"ready":true'
test "$(curl -fsS http://localhost:8000/health | grep -o '"status":"ok"')" = '"status":"ok"'
test "$(curl -fsS http://localhost:8080/health | grep -o '"status":"ok"')" = '"status":"ok"'

echo "==> PASS"
