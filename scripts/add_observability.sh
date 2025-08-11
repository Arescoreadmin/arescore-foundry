#!/usr/bin/env bash
set -Eeuo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$REPO_ROOT"

# Locate FastAPI main.py (or pass MAIN_PY=…)
if [[ -n "${MAIN_PY:-}" ]]; then
  MAIN="$MAIN_PY"
else
  MAIN="$(grep -RIl --include='main.py' -E 'FastAPI\(' backend 2>/dev/null | head -n1 || true)"
fi

[[ -z "${MAIN:-}" || ! -f "$MAIN" ]] && { echo "❌ Could not find FastAPI main.py. Set MAIN_PY=…"; exit 1; }
echo "==> Target: $MAIN"

changed=0

# 2a) Prometheus metrics at /metrics
if ! grep -q 'prometheus_fastapi_instrumentator' "$MAIN"; then
  echo "==> Injecting Prometheus Instrumentator"
  awk '
    BEGIN {added=0}
    {print}
    /app *= *FastAPI/ && added==0 {
      print "";
      print "try:";
      print "    from prometheus_fastapi_instrumentator import Instrumentator";
      print "    Instrumentator().instrument(app).expose(app, include_in_schema=false)";
      print "except Exception as _e:";
      print "    # metrics optional; don\047t crash app if lib missing";
      print "    pass";
      print "";
      added=1
    }
  ' "$MAIN" > "$MAIN.tmp" && mv "$MAIN.tmp" "$MAIN"
  changed=1
fi

# 2b) Request-ID middleware (adds/propagates X-Request-ID)
if ! grep -q 'X-Request-ID' "$MAIN"; then
  echo "==> Injecting request-id middleware"
  cat >> "$MAIN" <<'PY'

# --- BEGIN: injected request-id middleware ---
import uuid
from starlette.middleware.base import BaseHTTPMiddleware

async def _rid_mw(request, call_next):
    rid = request.headers.get("X-Request-ID") or uuid.uuid4().hex
    response = await call_next(request)
    response.headers["X-Request-ID"] = rid
    return response

try:
    app.add_middleware(BaseHTTPMiddleware, dispatch=_rid_mw)
except Exception:
    pass
# --- END: injected request-id middleware ---
PY
  changed=1
fi

# 2c) Ensure dependency present (best-effort)
REQ="backend/orchestrator/requirements.txt"
if [[ -f "$REQ" ]] && ! grep -qi '^prometheus-fastapi-instrumentator' "$REQ"; then
  echo "prometheus-fastapi-instrumentator" >> "$REQ"
  echo "==> Added prometheus-fastapi-instrumentator to $REQ"
  changed=1
fi

if (( changed )); then
  echo "==> Rebuilding API (orchestrator)…"
  docker compose -f infra/docker-compose.yml build orchestrator
  docker compose -f infra/docker-compose.yml up -d orchestrator
  CID="$(docker compose -f infra/docker-compose.yml ps -q orchestrator || true)"
  if [[ -n "$CID" ]]; then
    echo "==> Waiting for healthy…"
    for i in {1..60}; do
      state="$(docker inspect --format '{{.State.Health.Status}}' "$CID" 2>/dev/null || echo unknown)"
      [[ "$state" == "healthy" ]] && { echo "    healthy ✅"; break; }
      [[ "$state" == "unhealthy" ]] && { echo "    unhealthy ❌"; break; }
      sleep 2
    done
    echo "==> Probing:"
    curl -fsS http://127.0.0.1:8000/metrics | head -n 3 || true
  fi
else
  echo "==> Nothing changed."
fi

echo "==> Observability ready."
