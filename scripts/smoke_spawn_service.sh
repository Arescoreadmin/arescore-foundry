#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

# Build & start spawn_service (and deps via compose)
docker compose up -d --build spawn_service

echo "[*] Waiting for spawn_service health on http://127.0.0.1:8005/health ..."
for i in {1..30}; do
  status=$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8005/health || true)

  if [[ "$status" == "200" ]]; then
    echo "[+] spawn_service is healthy (HTTP 200 from /health)"
    exit 0
  fi

  sleep 1
done

echo "[!] spawn_service failed health check after 30s (last HTTP status: ${status:-none})"
docker compose logs spawn_service | tail -n 100
exit 1
