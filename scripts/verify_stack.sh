#!/usr/bin/env bash
set -Eeuo pipefail

BASE="infra/docker-compose.yml"
OV1="infra/docker-compose.hardening.override.yml"   # optional
SVC_API="orchestrator"
SVC_WEB="frontend"

compose() {
  if [[ -f "$OV1" ]]; then docker compose -f "$BASE" -f "$OV1" "$@"
  else                       docker compose -f "$BASE"          "$@"
  fi
}

http_code() {
  curl -sS -o /dev/null -w '%{http_code}' "$1" || echo "000"
}

wait_healthy() {
  local svc="$1"
  local cid; cid="$(compose ps -q "$svc")"
  echo "=> waiting for $svc to be healthy…"
  for i in {1..60}; do
    state="$(docker inspect --format '{{.State.Health.Status}}' "$cid" 2>/dev/null || echo unknown)"
    [[ "$state" == "healthy"   ]] && { echo "   $svc: healthy ✅"; return 0; }
    [[ "$state" == "unhealthy" ]] && { echo "   $svc: unhealthy ❌"; docker logs --tail=200 "$cid" || true; return 1; }
    sleep 2
  done
  echo "   $svc: timeout ⏳"; docker logs --tail=200 "$cid" || true; return 1
}

echo "==> Bring stack up"
compose up -d $SVC_API $SVC_WEB >/dev/null

echo "==> Health gates"
wait_healthy "$SVC_API" || exit 1

echo "==> Probe API endpoints"
C_HEALTH="$(http_code http://127.0.0.1:8000/health)"
C_READYZ="$(http_code http://127.0.0.1:8000/readyz || true)"
C_HEALTHZ="$(http_code http://127.0.0.1:8000/_healthz || true)"
echo "   /health  -> $C_HEALTH (expect 200)"
echo "   /readyz  -> $C_READYZ (expect 200; 503 means a dep check failed)"
echo "   /_healthz-> $C_HEALTHZ (optional; 200 if you added the alias)"

[[ "$C_HEALTH" == "200" ]] || { echo "❌ /health not OK"; exit 1; }

echo "==> Verify FastAPI routes from inside container"
CID_API="$(compose ps -q $SVC_API)"
MSYS_NO_PATHCONV=1 docker exec -it "$CID_API" sh -lc '
python - <<PY
from fastapi.routing import APIRoute
import app.main as m
routes = sorted([r.path for r in m.app.routes if isinstance(r, APIRoute)])
print("   routes:", routes)
print("   has /readyz:", "/readyz" in routes)
print("   has /health:", "/health" in routes)
print("   has /_healthz:", "/_healthz" in routes)
PY' || true

echo "==> Probe frontend basics"
C_ROOT="$(http_code http://127.0.0.1:3000/)"
echo "   GET / -> $C_ROOT (expect 200)"

echo "==> Check gzip actually served for an asset"
CID_WEB="$(compose ps -q $SVC_WEB)"
ASSET_PATH="$(docker exec "$CID_WEB" sh -lc 'ls -1 /usr/share/nginx/html/assets/*.js 2>/dev/null | head -n1' || true)"
if [[ -n "${ASSET_PATH:-}" ]]; then
  REL="assets/$(basename "$ASSET_PATH")"
  HDRS="$(curl -sI --compressed "http://127.0.0.1:3000/$REL" | tr -d '\r')"
  echo "$HDRS" | grep -i '^Content-Encoding:' || true
  echo "$HDRS" | grep -i '^Cache-Control:'     || true
  echo "   (asset checked: /$REL)"
  echo "   .gz exists in image? " \
    $(docker exec "$CID_WEB" sh -lc "[ -f \"$ASSET_PATH.gz\" ] && echo yes || echo no")
else
  echo "   no JS asset found to test (did the build produce /assets/*.js?)"
fi

echo "==> Frontend -> API connectivity (service DNS inside compose)"
set +e
docker exec "$CID_WEB" sh -lc 'wget -qO- http://orchestrator:8000/health' | sed -e 's/^/   /'
RC=$?
set -e
if [[ $RC -ne 0 ]]; then
  echo "   ⚠️ could not query orchestrator from frontend container (check network or wget availability)"
fi

echo "==> Optional metrics"
C_METRICS="$(http_code http://127.0.0.1:8000/metrics || true)"
if [[ "$C_METRICS" == "200" ]]; then
  echo "   /metrics -> 200 ✅"
else
  echo "   /metrics -> $C_METRICS (ok if you haven’t enabled instrumentation)"
fi

echo "==> All checks done."
