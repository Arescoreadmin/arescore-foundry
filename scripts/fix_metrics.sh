#!/usr/bin/env bash
set -Eeuo pipefail

# Target the orchestrator FastAPI entrypoint unless MAIN_PY is set.
MAIN="${MAIN_PY:-backend/orchestrator/app/main.py}"
REQ="${REQ_FILE:-backend/orchestrator/requirements.txt}"

[ -f "$MAIN" ] || { echo "❌ main.py not found at $MAIN (set MAIN_PY=...)"; exit 1; }

echo "=> Fixing include_in_schema casing in $MAIN (False)"
# change 'include_in_schema=false' -> 'include_in_schema=False'
# only within lines referencing Instrumentator().expose or add_api_route for /metrics
perl -0777 -pe 's/include_in_schema\s*=\s*false/include_in_schema=False/g' -i "$MAIN"

# If the earlier script injected a lowercase false anywhere else, fix those too.
perl -0777 -pe 's/include_in_schema\s*=\s*false/include_in_schema=False/g' -i "$MAIN"

# Ensure the instrumentator exists in requirements
if [ -f "$REQ" ] && ! grep -qi '^prometheus-fastapi-instrumentator' "$REQ"; then
  echo "prometheus-fastapi-instrumentator" >> "$REQ"
  echo "=> Added prometheus-fastapi-instrumentator to $REQ"
fi

echo "=> Rebuilding orchestrator..."
docker compose -f infra/docker-compose.yml build orchestrator
docker compose -f infra/docker-compose.yml up -d orchestrator

CID="$(docker compose -f infra/docker-compose.yml ps -q orchestrator || true)"
if [ -n "$CID" ]; then
  echo "=> Waiting for healthy..."
  for i in {1..60}; do
    state="$(docker inspect --format '{{.State.Health.Status}}' "$CID" 2>/dev/null || echo unknown)"
    [ "$state" = "healthy" ] && { echo "   healthy ✅"; break; }
    [ "$state" = "unhealthy" ] && { echo "   unhealthy ❌"; docker logs --tail=200 "$CID"; exit 1; }
    sleep 2
  done
  echo "=> Probe /metrics (first lines):"
  curl -fsS http://127.0.0.1:8000/metrics | head -n 5 || echo "metrics not exposed (lib missing?)"
fi
