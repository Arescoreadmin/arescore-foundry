#!/usr/bin/env bash
set -euo pipefail

svc=${1:-orchestrator}

echo "Starting services..."
docker compose up -d

echo "Killing $svc to demonstrate auto-restart..."
docker kill "$(docker compose ps -q "$svc")"

# give Docker a moment to restart
sleep 5

echo "Current service status:"
docker compose ps
