#!/usr/bin/env bash
set -Eeuo pipefail

ok() { printf "   %s ✓\n" "$1"; }
warn() { printf "   ⚠ %s\n" "$1"; }
fail() { printf "   ✗ %s\n" "$1"; exit 1; }

compose="docker compose -f infra/docker-compose.yml"
[[ -f infra/docker-compose.hardening.override.yml ]] && compose+=" -f infra/docker-compose.hardening.override.yml"
[[ -f infra/docker-compose.frontend-tmpfs.override.yml ]] && compose+=" -f infra/docker-compose.frontend-tmpfs.override.yml"
[[ -f infra/docker-compose.prometheus.yml ]] && compose+=" -f infra/docker-compose.prometheus.yml"

echo "==> Bring base stack up"
eval "$compose up -d orchestrator frontend >/dev/null"

echo "==> Health gates"
CID_API=$(eval "$compose ps -q orchestrator")
for _ in {1..40}; do
  state=$(docker inspect --format '{{.State.Health.Status}}' "$CID_API" 2>/dev/null || echo "unknown")
  [[ "$state" == "healthy" ]] && { ok "orchestrator healthy"; break; }
  sleep 1
done

echo "==> Probe API"
curl -fsS http://127.0.0.1:8000/health   >/dev/null && ok "/health 200" || fail "/health"
curl -fsS http://127.0.0.1:8000/_healthz >/dev/null && ok "/_healthz 200" || fail "/_healthz"
curl -fsS http://127.0.0.1:8000/readyz   >/dev/null && ok "/readyz 200" || fail "/readyz"
curl -fsS http://127.0.0.1:8000/metrics  >/dev/null && ok "/metrics 200" || fail "/metrics"

echo "==> Check health endpoints excluded from request metrics"
if curl -fsS http://127.0.0.1:8000/metrics \
 | grep -E 'http_requests_total|http_request_duration_seconds' \
 | grep -Eq '(^|/)(health|_healthz|readyz)($|")'; then
  warn "health endpoints still present in request metrics"
else
  ok "health endpoints excluded"
fi

echo "==> Frontend gzip"
curl -fsS http://127.0.0.1:3000/ >/dev/null && ok "frontend 200" || warn "frontend not reachable"
enc=$(curl -sI --compressed http://127.0.0.1:3000/ | tr -d '\r' | awk -F': ' 'tolower($1)=="content-encoding"{print $2}')
[[ "$enc" == "gzip" ]] && ok "gzip enabled" || warn "gzip not detected"

if [[ -f infra/docker-compose.prometheus.yml ]]; then
  echo "==> Observability checks"
  eval "$compose up -d prometheus alertmanager grafana >/dev/null"

  for _ in {1..40}; do
    curl -fsS http://127.0.0.1:9090/-/ready >/dev/null && { ok "Prometheus ready"; break; }; sleep 1
  done
  curl -fsS http://127.0.0.1:9090/api/v1/targets | grep -q '"health":"up"' && ok "orchestrator target UP" || warn "orchestrator target not UP"

  for _ in {1..40}; do
    curl -fsS http://127.0.0.1:9093/-/ready >/dev/null && { ok "Alertmanager ready"; break; }; sleep 1
  done

  for _ in {1..40}; do
    curl -fsS http://127.0.0.1:3001/api/health >/dev/null && { ok "Grafana ready"; break; }; sleep 1
  done

  # Watchdog present?
  curl -fsS http://127.0.0.1:9090/api/v1/alerts | grep -q '"alertname":"Watchdog"' \
    && ok "Watchdog alert active" \
    || warn "Watchdog not active yet"
fi

echo "==> Done."
