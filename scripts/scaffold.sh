#!/bin/bash
set -e

INFRA_DIR="./infra"
BACKEND_DIR="."

# Define services and their ports
services=(
  orchestrator
  sentinel_core
  sentinel_red
  log_indexer
)

declare -A svc_ports=(
  [orchestrator]=8000
  [sentinel_core]=8001
  [sentinel_red]=8002
  [log_indexer]=8003
)

echo "== Cleaning existing Dockerfiles and docker-compose.yml =="
rm -f "$INFRA_DIR"/*.Dockerfile
rm -f docker-compose.yml

echo "== Recreating Dockerfiles =="
for svc in "${services[@]}"; do
  cat > "$INFRA_DIR/${svc}.Dockerfile" <<DOCKER
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY $BACKEND_DIR/$svc/ .
EXPOSE ${svc_ports[$svc]}
RUN useradd -m appuser
USER appuser
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "${svc_ports[$svc]}"]
DOCKER
  echo "Created Dockerfile for $svc"
done

echo "== Creating docker-compose.yml =="
cat > docker-compose.yml <<'COMPOSE'
version: "3.9"

x-service-base: &service-base
  restart: unless-stopped
  env_file:
    - .env
  networks:
    - app_net

x-healthcheck-curl: &healthcheck-curl
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 10s

services:
COMPOSE

for svc in "${services[@]}"; do
  cat >> docker-compose.yml <<COMPOSE
  $svc:
    <<: *service-base
    build:
      context: .
      dockerfile: infra/${svc}.Dockerfile
    container_name: $svc
    ports:
      - "${svc_ports[$svc]}:${svc_ports[$svc]}"
COMPOSE

  if [[ "$svc" != "log_indexer" ]]; then
    cat >> docker-compose.yml <<COMPOSE
    depends_on:
      log_indexer:
        condition: service_healthy
COMPOSE
    if [[ "$svc" == "orchestrator" ]]; then
      cat >> docker-compose.yml <<COMPOSE
      sentinel_core:
        condition: service_started
      sentinel_red:
        condition: service_started
COMPOSE
    fi
  fi

  cat >> docker-compose.yml <<COMPOSE
    healthcheck:
      <<: *healthcheck-curl
      test: ["CMD-SHELL", "curl -fsS http://localhost:${svc_ports[$svc]}/health || exit 1"]
COMPOSE

  if [[ "$svc" == "log_indexer" ]]; then
    cat >> docker-compose.yml <<COMPOSE
    volumes:
      - log_data:/var/log/sentinel_foundry/
COMPOSE
  fi

done

cat >> docker-compose.yml <<'COMPOSE'

volumes:
  log_data:
    driver: local

networks:
  app_net:
    driver: bridge
COMPOSE

echo "== Scaffold complete =="
