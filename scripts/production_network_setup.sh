#!/bin/bash

# Create production networks with proper configuration
create_network() {
    local name=$1
    local subnet=$2
    local tier=$3

    if ! docker network inspect "$name" &>/dev/null; then
        echo "Creating production network: $name"
        docker network create "$name" \
            --driver bridge \
            --attachable \
            --subnet "$subnet" \
            --gateway "${subnet%.*}.1" \
            --label "tier=$tier" \
            --label "environment=production" \
            --label "com.docker.compose.network=$name"
    else
        echo "Network $name already exists - updating labels"
        docker network update "$name" \
            --label-add "tier=$tier" \
            --label-add "environment=production" \
            --label-add "com.docker.compose.network=$name"
    fi
}

# Create application network
create_network "appnet" "10.1.0.0/16" "application"

# Create infrastructure network
create_network "infra_appnet" "10.2.0.0/16" "infrastructure"

# Update compose files for production
update_compose_files() {
    # Remove obsolete version from override file
    sed -i '/^version:/d' infra/docker-compose.override.yml

    # Update main compose file for appnet
    cat <<EOF > infra/docker-compose.yml
version: '3.8'

services:
  observer_hub:
    build: ../backend/observer_hub
    environment:
      PROM_URL: \${PROM_URL:-http://prometheus:9090}
      ALERT_URL: \${ALERT_URL:-http://alertmanager:9093}
      LOG_INDEXER_URL: \${LOG_INDEXER_URL:-http://log_indexer:8081}
    ports:
      - "\${OBSERVER_PORT:-8070}:8070"
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "wget", "-qO-", "http://localhost:8070/health"]
      interval: 15s
      timeout: 5s
      retries: 5
      start_period: 10s
    networks:
      - appnet
    depends_on:
      - prometheus
      - alertmanager

  rca_ai:
    build: ../backend/rca_ai
    environment:
      LOG_INDEXER_URL: \${LOG_INDEXER_URL:-http://log_indexer:8081}
      ORCH_URL: \${ORCH_URL:-http://orchestrator:8000}
      OBSERVER_URL: \${OBSERVER_URL:-http://observer_hub:8070}
    ports:
      - "\${RCA_PORT:-8082}:8082"
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "wget", "-qO-", "http://localhost:8082/health"]
      interval: 15s
      timeout: 5s
      retries: 5
      start_period: 10s
    networks:
      - appnet
    depends_on:
      - observer_hub

  hardening_ai:
    build: ../backend/hardening_ai
    environment:
      REPO_URL: \${GIT_REPO:-}
      GITHUB_TOKEN: \${GITHUB_TOKEN:-}
      NGINX_DIR: /work/nginx
      INFRA_DIR: /work/infra
    volumes:
      - ../infra/nginx:/work/nginx
      - ../infra:/work/infra
    ports:
      - "\${HARDEN_PORT:-8083}:8083"
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "wget", "-qO-", "http://localhost:8083/health"]
      interval: 15s
      timeout: 5s
      retries: 5
      start_period: 10s
    networks:
      - appnet

  metrics_tuner:
    build: ../backend/metrics_tuner
    environment:
      PROM_URL: \${PROM_URL:-http://prometheus:9090}
      OUTPUT_RULES: /rules/_generated.yml
    volumes:
      - ../infra/prometheus/rules:/rules
    command: ["python", "/app/cron.py"]
    restart: unless-stopped
    networks:
      - appnet
      - infra_appnet
    depends_on:
      - prometheus

  attack_driver:
    build: ../backend/attack_driver
    environment:
      ORCH_URL: \${ORCH_URL:-http://orchestrator:8000}
      TARGET_NET: \${TARGET_NET:-default}
    ports:
      - "\${ATTACK_PORT:-8084}:8084"
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "wget", "-qO-", "http://localhost:8084/health"]
      interval: 15s
      timeout: 5s
      retries: 5
      start_period: 10s
    networks:
      - appnet

networks:
  appnet:
    external: true
  infra_appnet:
    external: true
EOF

    # Update prometheus compose file for infra_appnet
    cat <<EOF > infra/docker-compose.prometheus.yml
services:
  prometheus:
    image: prom/prometheus:latest
    container_name: infra-prometheus-1
    command:
      - --config.file=/etc/prometheus/prometheus.yml
      - --web.enable-lifecycle
      - --storage.tsdb.path=/prometheus
      - --storage.tsdb.retention.time=15d
      - --web.enable-admin-api
    volumes:
      - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - ./prometheus/rules:/etc/prometheus/rules:ro
      - ./prometheus/alerts:/etc/prometheus/alerts:ro
      - prometheus-data:/prometheus
    ports: 
      - "9090:9090"
    healthcheck:
      test: ["CMD", "wget", "--spider", "http://localhost:9090/-/healthy"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped
    networks:
      - infra_appnet

  alertmanager:
    image: prom/alertmanager:latest
    container_name: infra-alertmanager-1
    command:
      - --config.file=/etc/alertmanager/config.yml
      - --cluster.peer=alertmanager:9094
    volumes:
      - ./prometheus/alertmanager/config.yml:/etc/alertmanager/config.yml:ro
      - alertmanager-data:/alertmanager
    ports:
      - "9093:9093"
      - "9094:9094"
    healthcheck:
      test: ["CMD", "wget", "--spider", "http://localhost:9093/-/healthy"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped
    networks:
      - infra_appnet

  grafana:
    image: grafana/grafana:latest
    container_name: infra-grafana-1
    environment:
      - GF_SECURITY_ADMIN_USER=admin
      - GF_SECURITY_ADMIN_PASSWORD=\${GF_ADMIN_PASSWORD:-admin}
      - GF_USERS_DEFAULT_THEME=light
      - GF_PATHS_PROVISIONING=/etc/grafana/provisioning
      - GF_SERVER_DOMAIN=localhost
      - GF_SERVER_ROOT_URL=%(protocol)s://%(domain)s:%(http_port)s/grafana
    volumes:
      - grafana-data:/var/lib/grafana
      - ./grafana/provisioning/datasources:/etc/grafana/provisioning/datasources:ro
      - ./grafana/provisioning/dashboards:/etc/grafana/provisioning/dashboards:ro
      - ./grafana/dashboards:/var/lib/grafana/dashboards:ro
    ports:
      - "3001:3000"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    depends_on:
      prometheus:
        condition: service_healthy
    restart: unless-stopped
    networks:
      - infra_appnet

volumes:
  prometheus-data:
    driver: local
  grafana-data:
    driver: local
  alertmanager-data:
    driver: local

networks:
  infra_appnet:
    external: true
EOF

    # Clean up override file
    cat <<EOF > infra/docker-compose.override.yml
# Environment-specific overrides
# Add production-specific configurations here
EOF
}

# Update all compose files
update_compose_files

echo -e "\n✅ Production network setup complete"
echo "Networks created/updated:"
docker network ls --filter "name=appnet" --filter "name=infra_appnet"

echo -e "\nStart your stack with:"
echo "docker compose -f infra/docker-compose.yml -f infra/docker-compose.prometheus.yml -f infra/docker-compose.override.yml up -d"