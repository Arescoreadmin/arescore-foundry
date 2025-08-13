#!/usr/bin/env bash
set -Eeuo pipefail

MAIN_PY="${MAIN_PY:-backend/orchestrator/app/main.py}"

if [[ ! -f "$MAIN_PY" ]]; then
  echo "❌ Can't find $MAIN_PY (set MAIN_PY=... if different)"; exit 1
fi

echo "=> Patching Instrumentator in $MAIN_PY"
cp "$MAIN_PY" "$MAIN_PY.bak"

# Only patch if not already excluded
if grep -q "excluded_handlers=" "$MAIN_PY"; then
  echo "   already has excluded_handlers — skipping edit"
else
  # Replace the simple call with one that excludes health endpoints
  sed -i \
    's#Instrumentator().instrument(app).expose(app, include_in_schema=False)#Instrumentator(excluded_handlers=[r"/metrics", r"/health", r"/_healthz", r"/readyz"]).instrument(app).expose(app, include_in_schema=False)#' \
    "$MAIN_PY"
fi

echo "=> Rebuilding API container"
docker compose -f infra/docker-compose.yml build orchestrator >/dev/null

echo "=> Restarting API"
docker compose -f infra/docker-compose.yml up -d orchestrator >/dev/null

# Wait for healthy
CID="$(docker compose -f infra/docker-compose.yml ps -q orchestrator)"
echo -n "=> Waiting for healthy… "
for i in {1..60}; do
  state="$(docker inspect --format '{{.State.Health.Status}}' "$CID" 2>/dev/null || echo starting)"
  [[ "$state" == "healthy" ]] && { echo "healthy ✅"; break; }
  [[ "$state" == "unhealthy" ]] && { echo "unhealthy ❌"; docker logs --tail=100 "$CID"; exit 1; }
  sleep 1
done

echo "=> Verifying metrics no longer include health endpoints"
if curl -fsS http://127.0.0.1:8000/metrics | grep -E 'http_requests_total|http_request_duration_seconds' | grep -E '/(_healthz|health|readyz)'; then
  echo "❌ Health endpoints still present in metrics (check the patch)."
  exit 1
else
  echo "✅ Health endpoints excluded from metrics."
fi

echo "=> Spot check API:"
curl -fsS http://127.0.0.1:8000/health >/dev/null && echo "   /health 200 ✓"
curl -fsS http://127.0.0.1:8000/readyz >/dev/null && echo "   /readyz 200 ✓"
