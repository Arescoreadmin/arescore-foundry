#!/usr/bin/env bash
set -Eeuo pipefail

need() { command -v "$1" >/dev/null 2>&1 || { echo "Missing $1"; exit 1; }; }
need docker
need curl

# Compose files (base + prom override + any others if present)
compose_files=(-f infra/docker-compose.yml)
[[ -f infra/docker-compose.prometheus.yml ]] || {
  echo "=> Writing infra/docker-compose.prometheus.yml"
  cat > infra/docker-compose.prometheus.yml <<'YAML'
services:
  prometheus:
    image: prom/prometheus:latest
    command:
      - --config.file=/etc/prometheus/prometheus.yml
      - --web.enable-lifecycle
      - --storage.tsdb.path=/prometheus
      - --storage.tsdb.retention.time=15d
    volumes:
      - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus-data:/prometheus
    ports:
      - "9090:9090"
    depends_on:
      orchestrator:
        condition: service_healthy
    networks: [appnet]

  grafana:
    image: grafana/grafana:latest
    environment:
      - GF_SECURITY_ADMIN_USER=admin
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_USERS_DEFAULT_THEME=light
      - GF_PATHS_PROVISIONING=/etc/grafana/provisioning
    volumes:
      - grafana-data:/var/lib/grafana
      - ./grafana/provisioning/datasources:/etc/grafana/provisioning/datasources:ro
      - ./grafana/provisioning/dashboards:/etc/grafana/provisioning/dashboards:ro
      - ./grafana/dashboards:/var/lib/grafana/dashboards:ro
    ports:
      - "3001:3000"
    depends_on:
      - prometheus
    networks: [appnet]

volumes:
  prometheus-data:
  grafana-data:
YAML
}

for f in \
  infra/docker-compose.hardening.override.yml \
  infra/docker-compose.frontend-tmpfs.override.yml \
  infra/docker-compose.prometheus.yml
do
  [[ -f "$f" ]] && compose_files+=(-f "$f")
done

mkdir -p infra/prometheus infra/grafana/provisioning/{datasources,dashboards} infra/grafana/dashboards

# Prometheus config
if [[ ! -f infra/prometheus/prometheus.yml ]]; then
  echo "=> Writing infra/prometheus/prometheus.yml"
  cat > infra/prometheus/prometheus.yml <<'YAML'
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'orchestrator'
    metrics_path: /metrics
    static_configs:
      - targets: ['orchestrator:8000']
YAML
fi

# Grafana provisioning
if [[ ! -f infra/grafana/provisioning/datasources/datasource.yml ]]; then
  echo "=> Writing Grafana datasource"
  cat > infra/grafana/provisioning/datasources/datasource.yml <<'YAML'
apiVersion: 1
datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: true
YAML
fi

if [[ ! -f infra/grafana/provisioning/dashboards/dashboards.yml ]]; then
  echo "=> Writing Grafana dashboards provisioning"
  cat > infra/grafana/provisioning/dashboards/dashboards.yml <<'YAML'
apiVersion: 1
providers:
  - name: 'FastAPI Dashboards'
    orgId: 1
    folder: 'FastAPI'
    type: file
    updateIntervalSeconds: 30
    options:
      path: /var/lib/grafana/dashboards
YAML
fi

# Starter dashboard
if [[ ! -f infra/grafana/dashboards/fastapi-overview.json ]]; then
  echo "=> Writing starter FastAPI dashboard"
  cat > infra/grafana/dashboards/fastapi-overview.json <<'JSON'
{
  "uid": "fastapi-overview",
  "title": "FastAPI • Overview",
  "timezone": "browser",
  "schemaVersion": 39,
  "version": 1,
  "refresh": "10s",
  "time": { "from": "now-3h", "to": "now" },
  "panels": [
    {
      "type": "stat",
      "title": "Target UP (Prometheus)",
      "gridPos": { "x": 0, "y": 0, "w": 6, "h": 4 },
      "targets": [{ "expr": "up{job=\"orchestrator\"}", "legendFormat": "orchestrator" }]
    },
    {
      "type": "timeseries",
      "title": "Request rate by handler (req/s)",
      "gridPos": { "x": 6, "y": 0, "w": 18, "h": 8 },
      "targets": [{ "expr": "sum by (handler) (rate(http_requests_total[5m]))", "legendFormat": "{{handler}}" }]
    },
    {
      "type": "timeseries",
      "title": "Error rate (5xx) by handler",
      "gridPos": { "x": 0, "y": 4, "w": 12, "h": 8 },
      "targets": [{ "expr": "sum by (handler) (rate(http_requests_total{status=~\"5..\"}[5m]))", "legendFormat": "{{handler}}" }]
    },
    {
      "type": "timeseries",
      "title": "Latency p50 / p90 / p99 (s)",
      "gridPos": { "x": 12, "y": 8, "w": 12, "h": 8 },
      "targets": [
        { "expr": "histogram_quantile(0.50, sum by (le) (rate(http_request_duration_seconds_bucket[5m])))", "legendFormat": "p50" },
        { "expr": "histogram_quantile(0.90, sum by (le) (rate(http_request_duration_seconds_bucket[5m])))", "legendFormat": "p90" },
        { "expr": "histogram_quantile(0.99, sum by (le) (rate(http_request_duration_seconds_bucket[5m])))", "legendFormat": "p99" }
      ]
    },
    {
      "type": "timeseries",
      "title": "GC collected objects /s",
      "gridPos": { "x": 0, "y": 12, "w": 12, "h": 8 },
      "targets": [{ "expr": "sum(rate(python_gc_objects_collected_total[5m]))", "legendFormat": "gc collected" }]
    },
    {
      "type": "table",
      "title": "Top endpoints by error rate",
      "gridPos": { "x": 12, "y": 16, "w": 12, "h": 8 },
      "targets": [{ "expr": "topk(10, sum by (handler) (rate(http_requests_total{status=~\"5..\"}[5m])))", "legendFormat": "{{handler}}" }]
    }
  ]
}
JSON
fi

compose() { docker compose "${compose_files[@]}" "$@"; }

echo "=> Bringing up stack with Prometheus + Grafana…"
compose up -d prometheus grafana >/dev/null

echo "=> Waiting for Prometheus…"
for _ in {1..30}; do
  if curl -fsS http://127.0.0.1:9090/-/ready >/dev/null; then
    echo "   Prometheus ready ✓"; break
  fi
  sleep 1
done

echo "=> Checking Prometheus target"
targets="$(curl -s http://127.0.0.1:9090/api/v1/targets || true)"
echo "$targets" | grep -q '"scrapeUrl":"http://orchestrator:8000/metrics"' && echo "   orchestrator target present ✓" || echo "   ⚠ orchestrator target missing"
echo "$targets" | grep -q '"health":"up"' && echo "   orchestrator UP ✓" || echo "   ⚠ orchestrator not UP yet"

echo "=> Waiting for Grafana…"
for _ in {1..30}; do
  if curl -fsS http://127.0.0.1:3001/api/health >/dev/null; then
    echo "   Grafana up ✓"; break
  fi
  sleep 1
done

echo
echo "Open Grafana:  http://127.0.0.1:3001  (admin / admin)"
echo "Dashboard:     FastAPI • Overview  (folder: FastAPI)"
echo "Prometheus:    http://127.0.0.1:9090"
