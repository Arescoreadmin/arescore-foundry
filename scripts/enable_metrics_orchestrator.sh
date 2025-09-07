#!/usr/bin/env bash
set -Eeuo pipefail

MAIN="${MAIN_PY:-backend/orchestrator/app/main.py}"
REQ="${REQ_FILE:-backend/orchestrator/requirements.txt}"
BASE="infra/docker-compose.yml"
SVC="orchestrator"

[ -f "$MAIN" ] || { echo "❌ main.py not found at $MAIN (set MAIN_PY=...)"; exit 1; }

echo "=> Ensuring dependency in $REQ"
if [ -f "$REQ" ] && ! grep -qi '^prometheus-fastapi-instrumentator' "$REQ"; then
  printf '\nprometheus-fastapi-instrumentator\n' >> "$REQ"
fi

echo "=> Injecting Instrumentator into $MAIN (idempotent)"
if ! grep -q 'prometheus_fastapi_instrumentator' "$MAIN"; then
  # Insert right after first 'app = FastAPI(' line
  awk '
    added==1 { print; next }
    /app[[:space:]]*=[[:space:]]*FastAPI\(/ && added==0 {
      print
      print ""
      print "from prometheus_fastapi_instrumentator import Instrumentator"
      print ""
      print "# Prometheus metrics endpoint at /metrics"
      print "Instrumentator().instrument(app).expose(app, include_in_schema=False)"
      added=1
      next
    }
    { print }
  ' "$MAIN" > "$MAIN.tmp" && mv "$MAIN.tmp" "$MAIN"
else
  # Make sure include_in_schema is the right casing if already present
  perl -0777 -pe 's/include_in_schema\s*=\s*false/include_in_schema=False/g' -i "$MAIN"
fi

echo "=> Rebuilding API..."
docker compose -f "$BASE" build "$SVC" >/dev/null
docker compose -f "$BASE" up -d "$SVC" >/dev/null

CID="$(docker compose -f "$BASE" ps -q "$SVC")"
echo "=> Waiting for healthy..."
for i in {1..60}; do
  state="$(docker inspect --format '{{.State.Health.Status}}' "$CID" 2>/dev/null || echo unknown)"
  [ "$state" = "healthy" ] && { echo "   healthy ✅"; break; }
  [ "$state" = "unhealthy" ] && { echo "   unhealthy ❌"; docker logs --tail=200 "$CID"; exit 1; }
  sleep 2
done

echo "=> Probe /metrics (first lines):"
set +e
curl -fsS http://127.0.0.1:8000/metrics | head -n 5
RC=$?
set -e
if [ $RC -ne 0 ]; then
  echo "!! /metrics still 404 — showing registered routes to debug:"
  docker exec "$CID" python - <<'PY'
from fastapi.routing import APIRoute
import app.main as m
print([r.path for r in m.app.routes if isinstance(r, APIRoute)])
PY
  exit 2
fi

echo "=> Metrics OK."
