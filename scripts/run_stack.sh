#!/bin/bash

# Name: run_stack.sh
# Purpose: Navigate to project root and launch the Docker Compose stack reliably

# Expected project root
PROJECT_ROOT="arescore-foundry"
COMPOSE_FILES=("infra/docker-compose.yml" "infra/docker-compose.prometheus.yml" "infra/docker-compose.override.yml")

# Navigate to project root if script is run from inside /scripts or deeper
while [ ! -f "${COMPOSE_FILES[0]}" ]; do
  if [ "$PWD" == "/" ]; then
    echo "❌ Reached root directory — cannot find project root containing docker-compose.yml"
    exit 1
  fi
  cd ..
done

# Verify all required compose files exist
for file in "${COMPOSE_FILES[@]}"; do
  if [ ! -f "$file" ]; then
    echo "❌ Missing compose file: $file"
    exit 1
  fi
done

# Launch the stack
echo "🚀 Starting Docker Compose stack from $(pwd)..."
docker compose \
  -f infra/docker-compose.yml \
  -f infra/docker-compose.prometheus.yml \
  -f infra/docker-compose.override.yml \
  up -d

if [ $? -eq 0 ]; then
  echo "✅ Stack launched successfully"
else
  echo "❌ Failed to launch stack"
  exit 1
fi
