# scripts/enable_metrics_clean.sh
#!/usr/bin/env bash
set -Eeuo pipefail

MAIN="backend/orchestrator/app/main.py"
REQS="backend/orchestrator/requirements.txt"

echo "=> Ensuring dependency"
grep -q '^prometheus-fastapi-instrumentator' "$REQS" || \
  echo 'prometheus-fastapi-instrumentator>=6.1.0' >> "$REQS"

echo "=> Removing any previous managed metrics block"
perl -0777 -pe 's/# --- BEGIN auto metrics wiring .*?# --- END auto metrics wiring ---\n//s' -i "$MAIN" || true
perl -0777 -pe 's/# --- BEGIN: health-metrics-exclude .*?# --- END: health-metrics-exclude ---\n//s' -i "$MAIN" || true

echo "=> Injecting clean, idempotent metrics wiring"
if ! grep -q 'BEGIN auto metrics wiring (clean)' "$MAIN"; then
  cat >>"$MAIN" <<'PY'
# --- BEGIN auto metrics wiring (clean) ---
try:
    import logging
    from prometheus_fastapi_instrumentator import Instrumentator  # type: ignore[import-not-found]

    # Avoid double-expose if hot-reload or multiple init
    _already = any(getattr(r, "path", "") == "/metrics" for r in getattr(app, "routes", []))
    if not _already:
        Instrumentator(
            should_group_status_codes=True,
            excluded_handlers=[r"^/metrics$", r"^/health$", r"^/_healthz$", r"^/readyz$"],
        ).instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)
        logging.getLogger(__name__).info("Prometheus metrics enabled at /metrics (health endpoints excluded)")
except Exception as _e:  # pragma: no cover
    import logging as _logging
    _logging.getLogger(__name__).warning("Prometheus metrics not enabled: %s", _e)
# --- END auto metrics wiring (clean) ---
PY
fi

echo "=> Quick syntax check"
python -m py_compile "$MAIN"

echo "=> Rebuild + restart API"
docker compose -f infra/docker-compose.yml up -d --build orchestrator

echo "=> Wait for healthy"
CID=$(docker compose -f infra/docker-compose.yml ps -q orchestrator)
until [[ "$(docker inspect --format '{{.State.Health.Status}}' "$CID")" == "healthy" ]]; do
  sleep 1
done
echo "   healthy ✓"

echo "=> Verify /metrics"
curl -fsS http://127.0.0.1:8000/metrics >/dev/null && echo "metrics 200 ✓" || (echo "metrics missing ❌"; exit 1)

echo "=> Ensure health endpoints are NOT in request metrics"
curl -s http://127.0.0.1:8000/metrics | \
  grep -E 'http_requests_total|http_request_duration_seconds' | \
  grep -E '(^|/)(health|_healthz|readyz)($|")' >/dev/null && \
  (echo "health endpoints leaked into metrics ❌"; exit 2) || \
  echo "health endpoints excluded ✓"
