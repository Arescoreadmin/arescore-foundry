#!/usr/bin/env bash
set -Eeuo pipefail

need() { command -v "$1" >/dev/null 2>&1 || { echo "Missing $1"; exit 1; }; }
need docker
need curl

mkdir -p infra/prometheus/rules infra/prometheus/alerts infra/prometheus/alertmanager
mkdir -p infra/grafana/provisioning/{datasources,dashboards} infra/grafana/dashboards

# sanity check base compose exists
[[ -f infra/docker-compose.yml ]] || { echo "infra/docker-compose.yml missing"; exit 1; }

echo "=> Bringing up Prometheus + Alertmanager + Grafana…"
docker compose \
  -f infra/docker-compose.yml \
  -f infra/docker-compose.prometheus.yml \
  up -d prometheus alertmanager grafana

echo "=> Wait for Prometheus readiness…"
for _ in {1..40}; do
  if curl -fsS http://127.0.0.1:9090/-/ready >/dev/null; then
    echo "   Prometheus ready ✓"; break
  fi; sleep 1
done

echo "=> Check rules loaded…"
curl -fsS http://127.0.0.1:9090/api/v1/rules >/dev/null && echo "   Rules API OK ✓"

echo "=> Check targets…"
targets="$(curl -fsS http://127.0.0.1:9090/api/v1/targets)"
echo "$targets" | grep -q '"orchestrator:8000"' && echo "   Orchestrator target present ✓" || echo "   ⚠ target missing"
echo "$targets" | grep -q '"health":"up"' && echo "   Orchestrator UP ✓" || echo "   ⚠ not UP yet"

echo "=> Wait for Alertmanager…"
for _ in {1..40}; do
  if curl -fsS http://127.0.0.1:9093/-/ready >/dev/null; then
    echo "   Alertmanager ready ✓"; break
  fi; sleep 1
done

echo "=> Check active alerts (should see Watchdog)…"
curl -fsS http://127.0.0.1:9090/api/v1/alerts | jq . 2>/dev/null || curl -fsS http://127.0.0.1:9090/api/v1/alerts

echo "=> Wait for Grafana…"
for _ in {1..40}; do
  if curl -fsS http://127.0.0.1:3001/api/health >/dev/null; then
    echo "   Grafana up ✓"; break
  fi; sleep 1
done

cat <<EOF

All set ✅

Prometheus  http://127.0.0.1:9090
Alertmanager http://127.0.0.1:9093
Grafana      http://127.0.0.1:3001  (admin / admin)

Tip:
- Replace the 'noop' receiver in infra/prometheus/alertmanager/config.yml with your Slack/email/webhook.
- To reload Prometheus after editing rules:
    curl -X POST http://127.0.0.1:9090/-/reload
EOF
