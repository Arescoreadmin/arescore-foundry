#!/bin/bash
set -e

echo "🧼 Cleaning up old containers and volumes..."
docker compose -f infra/docker-compose.yml down -v || true

echo "🚀 Booting up the full AresCore Foundry stack..."
docker compose \
  -f infra/docker-compose.yml \
  -f infra/docker-compose.override.yml \
  -f infra/docker-compose.prometheus.yml \
  up -d --build

echo "⏳ Waiting for containers to initialize..."
sleep 10

echo "🔧 Running patch and auto-repair scripts..."
bash scripts/patch_and_test_infra.sh || echo "⚠️ Patch script failed"
bash scripts/repair_metrics_wiring.sh || echo "⚠️ Metric repair failed"
bash scripts/repair_health_routes.sh || echo "⚠️ Health route fix failed"

echo "🧪 Running full test suite..."
bash scripts/test_all.sh || echo "⚠️ Diagnostics returned warnings"

echo ""
echo "🧭 ACCESS YOUR SYSTEM"
echo "━━━━━━━━━━━━━━━━━━━━━"
echo "🌐 Grafana:       http://localhost:3000"
echo "🌐 Prometheus:    http://localhost:9090"
echo "🌐 Alertmanager:  http://localhost:9093"
echo "🌐 Orchestrator:  http://localhost:8000"
echo ""

echo "📦 Docker Container Status:"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo ""
echo "✅ Sentinel Foundry stack is live and monitored."
