#!/usr/bin/env bash
set -Eeuo pipefail

MAIN_PY="${MAIN_PY:-backend/orchestrator/app/main.py}"
COMPOSE="${COMPOSE:-infra/docker-compose.yml}"

[[ -f "$MAIN_PY" ]] || { echo "❌ Can't find $MAIN_PY (set MAIN_PY=...)" ; exit 1; }

echo "=> Backing up $MAIN_PY"
cp "$MAIN_PY" "$MAIN_PY.bak"

MARK="# --- BEGIN: health-metrics-exclude ---"
if grep -q "$MARK" "$MAIN_PY"; then
  echo "=> Exclude block already present — skipping insert"
else
  echo "=> Commenting out any existing Instrumentator wiring (non-destructive)"
  # Comment typical one-liners or split lines that call instrument().expose()
  sed -i \
    -e 's/^\(\s*\)\(Instrumentator(.*\)\?\s*\.instrument(app)\.expose(app[^)]*)\s*$/\1# DISABLED by script: \2.instrument(app).expose(app)/' \
    -e 's/^\(\s*\)Instrumentator(.*)$/\1# DISABLED by script: &/' \
    -e 's/^\(\s*\)\(\w\+\)\s*=\s*Instrumentator(.*)$/\1# DISABLED by script: \2 = Instrumentator(...)/' \
    "$MAIN_PY" || true

  echo "=> Ensuring import exists"
  grep -q 'prometheus_fastapi_instrumentator' "$MAIN_PY" || \
    sed -i '1s/^/from prometheus_fastapi_instrumentator import Instrumentator as _Instr\n/' "$MAIN_PY"

  echo "=> Appending robust exclude block"
  cat >>"$MAIN_PY" <<'PY'
# --- BEGIN: health-metrics-exclude ---
try:
    # Prefer both mechanisms to be extra safe across library versions.
    _instr = _Instr(
        excluded_handlers=[
            r"^/metrics$",
            r"^/health$",
            r"^/_healthz$",
            r"^/readyz$",
        ],
        should_ignore=lambda req: getattr(req, "url", None)
        and getattr(req.url, "path", "")
        in {"/metrics", "/health", "/_healthz", "/readyz"},
    )
    _instr.instrument(app).expose(app, include_in_schema=False)
except Exception as _e:
    # Keep the app booting even if metrics wiring fails
    pass
# --- END: health-metrics-exclude ---
PY
fi

echo "=> Rebuilding API"
docker compose -f "$COMPOSE" build orchestrator >/dev/null

echo "=> Restarting API"
docker compose -f "$COMPOSE" up -d orchestrator >/dev/null

CID="$(docker compose -f "$COMPOSE" ps -q orchestrator)"
echo -n "=> Waiting for healthy… "
for i in {1..60}; do
  state="$(docker inspect --format '{{.State.Health.Status}}' "$CID" 2>/dev/null || echo starting)"
  [[ "$state" == "healthy" ]] && { echo "healthy ✅"; break; }
  [[ "$state" == "unhealthy" ]] && { echo "unhealthy ❌"; docker logs --tail=120 "$CID"; exit 1; }
  sleep 1
done

echo "=> Verifying metrics exclude health endpoints"
if curl -fsS http://127.0.0.1:8000/metrics \
   | grep -E 'http_requests_total|http_request_duration_seconds' \
   | grep -E '/(_healthz|health|readyz)'; then
  echo "❌ Health endpoints still visible in metrics."
  echo "   Check that the new block executed (and no other Instrumentator() call remains active)."
  exit 1
else
  echo "✅ No health endpoints found in request metrics."
fi

echo "=> Spot check:"
curl -fsS http://127.0.0.1:8000/health >/dev/null && echo "   /health 200 ✓"
curl -fsS http://127.0.0.1:8000/readyz >/dev/null && echo "   /readyz 200 ✓"
