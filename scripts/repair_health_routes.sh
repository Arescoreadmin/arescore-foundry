# scripts/repair_health_routes.sh
#!/usr/bin/env bash
set -Eeuo pipefail

MAIN_PY="${MAIN_PY:-backend/orchestrator/app/main.py}"
COMPOSE="${COMPOSE:-infra/docker-compose.yml}"

[[ -f "$MAIN_PY" ]] || { echo "main.py not found: $MAIN_PY"; exit 1; }

echo "==> Backing up $MAIN_PY"
cp -f "$MAIN_PY" "$MAIN_PY.bak.$(date +%s)"

echo "==> Normalize line endings"
tmp="$(mktemp)"; tr -d '\r' < "$MAIN_PY" > "$tmp" && mv "$tmp" "$MAIN_PY"

echo "==> Remove any previous managed health block (if present)"
awk '
  BEGIN{drop=0}
  /# --- BEGIN managed health routes ---/ {drop=1; next}
  drop && /# --- END managed health routes ---/ {drop=0; next}
  !drop {print}
' "$MAIN_PY" > "$MAIN_PY.tmp" && mv "$MAIN_PY.tmp" "$MAIN_PY"

echo "==> Ensure imports (fastapi.status, JSONResponse) exist"
awk '
  BEGIN{haveStatus=0; haveResp=0}
  /from fastapi import .*status/ {haveStatus=1}
  /from fastapi\.responses import .*JSONResponse/ {haveResp=1}
  {lines[NR]=$0}
  END{
    for(i=1;i<=NR;i++) print lines[i]
    if(!haveStatus) print "from fastapi import status"
    if(!haveResp)   print "from fastapi.responses import JSONResponse"
  }
' "$MAIN_PY" > "$MAIN_PY.tmp" && mv "$MAIN_PY.tmp" "$MAIN_PY"

echo "==> Append clean health + readiness + alias block"
cat >>"$MAIN_PY" <<'PY'
# --- BEGIN managed health routes ---
@app.get("/health", include_in_schema=False)
def health():
    return {"status": "ok", "service": APP_NAME}

@app.get("/readyz", include_in_schema=False)
async def readyz():
    # TODO: add real dependency checks here
    ok = True
    code = status.HTTP_200_OK if ok else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse({"ready": ok, "service": APP_NAME}, status_code=code)

# Keep Kubernetes-style alias available
try:
    _paths = [getattr(r, "path", "") for r in getattr(app, "routes", [])]
    if "/_healthz" not in _paths:
        app.add_api_route("/_healthz", health, include_in_schema=False)
except Exception:
    pass
# --- END managed health routes ---
PY

echo "==> Local compile check"
python -m py_compile "$MAIN_PY"

echo "==> Rebuild + restart orchestrator"
docker compose -f "$COMPOSE" up -d --build orchestrator >/dev/null

CID="$(docker compose -f "$COMPOSE" ps -q orchestrator)"
echo "==> Wait for healthy"
for i in {1..60}; do
  s="$(docker inspect --format '{{.State.Health.Status}}' "$CID" 2>/dev/null || true)"
  [[ "$s" == "healthy" ]] && { echo "   healthy ✅"; break; }
  [[ "$s" == "unhealthy" ]] && { echo "   unhealthy ❌"; docker logs --tail=150 "$CID"; exit 1; }
  sleep 1
done

echo "==> Probe endpoints"
curl -fsS http://127.0.0.1:8000/health   >/dev/null && echo "   /health 200 ✓"
curl -fsS http://127.0.0.1:8000/_healthz >/dev/null && echo "   /_healthz 200 ✓"
curl -fsS http://127.0.0.1:8000/readyz   >/dev/null && echo "   /readyz 200 ✓"

echo "==> Done."
