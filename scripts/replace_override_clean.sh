#!/usr/bin/env bash
set -euo pipefail

OVR="infra/docker-compose.override.yml"
BACK="$OVR.bak.$(date +%Y%m%d-%H%M%S)"

echo "Backing up $OVR -> $BACK"
cp "$OVR" "$BACK" 2>/dev/null || true

cat > "$OVR" <<'YAML'
services:
  observer_hub:
    build: ../backend/observer_hub
    environment:
      PROM_URL: ${PROM_URL:-http://prometheus:9090}
      ALERT_URL: ${ALERT_URL:-http://alertmanager:9093}
      LOG_INDEXER_URL: ${LOG_INDEXER_URL:-http://log_indexer:8081}
    ports:
      - "${OBSERVER_PORT:-8070}:8070"
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "wget", "-qO-", "http://localhost:8070/health"]
      interval: 15s
      timeout: 5s
      retries: 5
      start_period: 10s
    networks: [appnet]
    depends_on:
      prometheus:
        condition: service_started
      alertmanager:
        condition: service_started

  rca_ai:
    build: ../backend/rca_ai
    environment:
      LOG_INDEXER_URL: ${LOG_INDEXER_URL:-http://log_indexer:8081}
      ORCH_URL: ${ORCH_URL:-http://orchestrator:8000}
      OBSERVER_URL: ${OBSERVER_URL:-http://observer_hub:8070}
    ports:
      - "${RCA_PORT:-8082}:8082"
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "wget", "-qO-", "http://localhost:8082/health"]
      interval: 15s
      timeout: 5s
      retries: 5
      start_period: 10s
    networks: [appnet]
    depends_on:
      observer_hub:
        condition: service_started

  hardening_ai:
    build: ../backend/hardening_ai
    environment:
      REPO_URL: ${GIT_REPO:-}
      GITHUB_TOKEN: ${GITHUB_TOKEN:-}
      NGINX_DIR: /work/nginx
      INFRA_DIR: /work/infra
    volumes:
      - ../infra/nginx:/work/nginx
      - ../infra:/work/infra
    ports:
      - "${HARDEN_PORT:-8083}:8083"
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "wget", "-qO-", "http://localhost:8083/health"]
      interval: 15s
      timeout: 5s
      retries: 5
      start_period: 10s
    networks: [appnet]

  metrics_tuner:
    build: ../backend/metrics_tuner
    environment:
      PROM_URL: ${PROM_URL:-http://prometheus:9090}
      OUTPUT_RULES: /rules/_generated.yml
    volumes:
      - ../infra/prometheus/rules:/rules
    command: ["python", "/app/cron.py"]
    restart: unless-stopped
    networks: [appnet]
    depends_on:
      prometheus:
        condition: service_started

  attack_driver:
    build: ../backend/attack_driver
    environment:
      ORCH_URL: ${ORCH_URL:-http://orchestrator:8000}
      TARGET_NET: ${TARGET_NET:-default}
    ports:
      - "${ATTACK_PORT:-8084}:8084"
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "wget", "-qO-", "http://localhost:8084/health"]
      interval: 15s
      timeout: 5s
      retries: 5
      start_period: 10s
    networks: [appnet]
YAML

# Normalize line endings (Windows safety)
sed -i 's/\r$//' "$OVR"

echo "Validating compose…"
docker compose -f infra/docker-compose.yml \
               -f infra/docker-compose.prometheus.yml \
               -f infra/docker-compose.override.yml \
               config --quiet || { echo "Compose validation failed"; exit 1; }

echo "Restarting stack…"
docker compose -p infra \
  -f infra/docker-compose.yml \
  -f infra/docker-compose.prometheus.yml \
  -f infra/docker-compose.override.yml \
  down

docker compose -p infra \
  -f infra/docker-compose.yml \
  -f infra/docker-compose.prometheus.yml \
  -f infra/docker-compose.override.yml \
  up -d

echo "OK. Tip: run ./scripts/diagnose_stack.sh to verify end-to-end."
