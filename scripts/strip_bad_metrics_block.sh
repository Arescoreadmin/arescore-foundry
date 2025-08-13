#!/usr/bin/env bash
set -Eeuo pipefail
FILE="backend/orchestrator/app/main.py"

# 1) Backup
cp -f "$FILE" "$FILE.bak.$(date +%s)"

# 2) Normalize line endings (Windows → Unix) without dos2unix
#    This prevents hidden CRs from breaking indentation checks.
tmp="$(mktemp)"; tr -d '\r' < "$FILE" > "$tmp" && mv "$tmp" "$FILE"

# 3) Delete the broken "Optional Prometheus metrics" try/except block only.
#    We remove from the marker comment down to the next '@app.' decorator,
#    keeping everything else (including your newer BEGIN/END wiring blocks).
awk '
  /# Optional Prometheus metrics/ {del=1; next}
  del && /^@app\./ {del=0}
  !del { print }
' "$FILE" > "$FILE.tmp" && mv "$FILE.tmp" "$FILE"

# 4) Sanity: compile locally before rebuilding the image
python -m py_compile "$FILE"

echo "=> Source compiles. Rebuilding orchestrator…"
docker compose -f infra/docker-compose.yml build orchestrator >/dev/null
docker compose -f infra/docker-compose.yml up -d orchestrator

echo "=> Waiting for healthy…"
CID="$(docker compose -f infra/docker-compose.yml ps -q orchestrator)"
for i in {1..30}; do
  s="$(docker inspect --format '{{.State.Health.Status}}' "$CID" 2>/dev/null || echo starting)"
  [[ "$s" == "healthy" ]] && { echo "   healthy ✅"; break; }
  [[ "$s" == "unhealthy" ]] && { echo "   unhealthy ❌"; docker logs --tail=120 "$CID"; exit 1; }
  sleep 1
done

echo "=> Probing endpoints…"
curl -fsS http://127.0.0.1:8000/health   >/dev/null && echo "   /health 200 ✓"
curl -fsS http://127.0.0.1:8000/_healthz >/dev/null && echo "   /_healthz 200 ✓"
curl -fsS http://127.0.0.1:8000/readyz   >/dev/null && echo "   /readyz 200 ✓"
curl -fsS http://127.0.0.1:8000/metrics  >/dev/null && echo "   /metrics 200 ✓"

# Optional: verify that health endpoints are excluded from metrics
echo "=> Checking metrics exclusion (no /_healthz|/readyz in http_requests_total)…"
if curl -fsS http://127.0.0.1:8000/metrics | grep -E 'http_requests_total\{.*handler="/(_healthz|readyz)"' >/dev/null; then
  echo "   ❌ Health endpoints still present in metrics"
  exit 1
else
  echo "   ✅ Health endpoints excluded from metrics"
fi
