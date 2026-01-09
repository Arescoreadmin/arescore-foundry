#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

echo "[*] Using compose files:"
echo "    - compose.yml"
echo "    - compose.federated.yml"
echo

echo "[*] Checking that 'minio' service exists in merged config..."
if ! docker compose -f compose.yml -f compose.federated.yml config | rg -q '^  minio:'; then
  echo "[!] 'minio' service is NOT defined in the merged compose config."
  echo "    This is why you see: 'no such service: minio'"
  echo
  echo "    Fix on this branch with:"
  echo "      git restore compose.yml compose.federated.yml"
  echo "      git diff -- compose.yml compose.federated.yml   # should be clean"
  exit 1
fi

echo "[+] 'minio' service found in compose config."
echo

echo "[*] Bringing up overlay stack (same pattern as CI)..."
docker compose -f compose.yml -f compose.federated.yml up -d --build

echo
echo "[*] Current containers:"
docker compose -f compose.yml -f compose.federated.yml ps

echo
echo "[*] Probing orchestrator /health on 127.0.0.1:8080..."
for i in {1..30}; do
  if curl -fsS http://127.0.0.1:8080/health >/dev/null 2>&1; then
    echo "[+] Orchestrator /health OK"
    exit 0
  fi
  sleep 1
done

echo
echo "[!] Orchestrator /health still failing after 30s. Recent logs:"
docker compose -f compose.yml -f compose.federated.yml logs orchestrator | tail -n 120
