#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

docker compose up -d --build spawn_service

echo "[*] Waiting for spawn_service health..."
for i in {1..20}; do
  if curl -fsS http://localhost:8005/health >/dev/null 2>&1; then
    echo "[+] spawn_service is healthy"
    exit 0
  fi
  sleep 1
done

echo "[!] spawn_service failed health check"
docker compose logs spawn_service | tail -n 100
exit 1
